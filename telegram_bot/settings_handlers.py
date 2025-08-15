#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot Settings Handlers
Handlers that allow users to change settings through the bot
"""

import logging
from typing import Dict, List, Optional, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

# Import conversation states from bot_core to avoid conflicts
# These constants MUST match bot_core.py exactly
WAITING_FOR_COIN_SYMBOL = 0
WAITING_FOR_CONFIRMATION = 1  
WAITING_FOR_TRADE_AMOUNT = 2
WAITING_FOR_SETTING_VALUE = 3

class SettingsHandlers:
    """Telegram bot settings command handlers"""
    
    def __init__(self, dynamic_settings_manager, telegram_bot):
        self.settings_manager = dynamic_settings_manager
        self.bot = telegram_bot
        self.user_sessions = {}  # Store user conversation state
        
        # Get settings configuration from manager
        self.settings_config = dynamic_settings_manager.get_user_configurable_settings()
        
        logger.info("Settings handlers initialized with JSON configuration")
    
    async def handle_settings_main(self, update_or_query, context=None):
        """Main settings menu"""
        try:
            # Build dynamic settings menu from JSON config
            settings_text = "⚙️ **Bot Settings Panel**\n\n"
            settings_text += "Choose a category to configure:\n\n"
            
            # Create category buttons from JSON config
            keyboard = []
            for category, cat_config in self.settings_config.items():
                title = cat_config.get('title', category.title())
                description = cat_config.get('description', '')
                button_text = f"{title}"
                if description:
                    settings_text += f"• **{title}**\n  {description}\n\n"
                
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"settings_category_{category}")])
            
            # Add utility buttons
            keyboard.extend([
                [InlineKeyboardButton("📊 Settings Status", callback_data="settings_status")],
                [InlineKeyboardButton("📤 Export Settings", callback_data="settings_export")],
                [InlineKeyboardButton("🔄 Reset Category", callback_data="settings_reset_menu")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = settings_text
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            else:
                await update_or_query.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Error showing settings main menu: {str(e)}")
            error_message = "❌ Error loading settings menu!"
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(error_message)
            else:
                await update_or_query.message.reply_text(error_message)
    
    async def handle_settings_category(self, update_or_query, category: str):
        """Show specific category settings"""
        try:
            # Get category configuration from JSON
            cat_config = self.settings_config.get(category)
            if not cat_config:
                await self._send_error_message(update_or_query, f"Category '{category}' not found!")
                return
                
            title = cat_config.get('title', category.title())
            description = cat_config.get('description', '')
            settings = cat_config.get('settings', {})
            
            if not settings:
                await self._send_error_message(update_or_query, f"No settings found for category '{category}'!")
                return
            
            # Build settings display
            settings_text = f"**{title}**\n\n"
            if description:
                settings_text += f"{description}\n\n"
            
            # Show current values
            for key, setting_config in settings.items():
                current_value = self.settings_manager.get_setting(category, key)
                setting_title = setting_config.get('title', key)
                setting_desc = setting_config.get('description', '')
                restart_required = setting_config.get('restart_required', False)
                
                # Format value display
                if setting_config.get('type') == 'boolean':
                    value_display = "✅ Enabled" if current_value else "❌ Disabled"
                elif setting_config.get('type') in ['number', 'integer']:
                    min_val = setting_config.get('min')
                    max_val = setting_config.get('max')
                    range_info = f" (Range: {min_val}-{max_val})" if min_val is not None and max_val is not None else ""
                    value_display = f"{current_value}{range_info}"
                else:
                    value_display = str(current_value)
                
                restart_indicator = " 🔄" if restart_required else ""
                
                settings_text += f"🔧 **{setting_title}**{restart_indicator}\n"
                settings_text += f"   {setting_desc}\n"
                settings_text += f"   Current: `{value_display}`\n\n"
            
            # Add restart note if needed
            restart_settings = [k for k, v in settings.items() if v.get('restart_required', False)]
            if restart_settings:
                settings_text += "\n🔄 = Requires restart to take effect"
            
            # Create keyboard
            keyboard = []
            
            # Setting edit buttons
            for key, setting_config in settings.items():
                setting_title = setting_config.get('title', key)
                button_text = f"✏️ {setting_title}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"settings_edit_{category}_{key}")])
            
            # Navigation buttons
            keyboard.extend([
                [InlineKeyboardButton("🔄 Reset Category", callback_data=f"settings_reset_category_{category}")],
                [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            else:
                await update_or_query.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        except Exception as e:
            logger.error(f"Error showing category {category}: {str(e)}")
            error_message = f"❌ Error loading {category} settings!"
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(error_message)
            else:
                await update_or_query.message.reply_text(error_message)
            
        except Exception as e:
            logger.error(f"Error showing category {category}: {str(e)}")
            await self._send_error_message(update_or_query, f"'{category}' error loading settings.")
    
    async def handle_setting_edit(self, update_or_query, category: str, key: str):
        """Edit specific setting"""
        try:
            # Get setting configuration from JSON
            setting_config = self.settings_manager.get_setting_config(category, key)
            
            if not setting_config:
                await self._send_error_message(update_or_query, f"Setting not found: {category}.{key}")
                return
            
            # Get current value
            current_value = self.settings_manager.get_setting(category, key)
            description = setting_config.get('description', '')
            setting_title = setting_config.get('title', key)
            setting_type = setting_config.get('type', 'string')
            min_val = setting_config.get('min')
            max_val = setting_config.get('max')
            restart_required = setting_config.get('restart_required', False)
            
            # Create edit interface based on setting type
            if setting_type == 'bool':
                # Boolean toggle
                new_value = not current_value
                success = self.settings_manager.set_setting(
                    category, key, new_value, 
                    user_id=self._get_user_id(update_or_query)
                )
                
                if success:
                    status = "✅ Active" if new_value else "❌ Inactive"
                    message = f"✅ **{description}** updated!\n\nNew value: {status}"
                    
                    if restart_required:
                        message += "\n\n🔄 **Warning:** Bot must be restarted for this change!"
                else:
                    message = f"❌ **{description}** could not be updated!"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"settings_category_{category}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self._send_or_edit_message(update_or_query, message, reply_markup)
                
            else:
                # Numeric input required
                range_info = ""
                if min_val is not None and max_val is not None:
                    range_info = f"({min_val} - {max_val})"
                elif min_val is not None:
                    range_info = f"(min: {min_val})"
                elif max_val is not None:
                    range_info = f"(max: {max_val})"
                
                message = f"""
✏️ **{description}** Edit

**Current value:** `{current_value}`
**Tip:** {setting_type} {range_info}

Enter new value or type 'cancel' to cancel.
                """
                
                keyboard = [
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"settings_category_{category}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self._send_or_edit_message(update_or_query, message, reply_markup)
                
                # Set conversation state
                user_id = self._get_user_id(update_or_query)
                self.user_sessions[user_id] = {
                    'state': WAITING_FOR_SETTING_VALUE,
                    'category': category,
                    'key': key,
                    'setting_config': setting_config
                }
                
        except Exception as e:
            logger.error(f"Error editing setting {category}.{key}: {str(e)}")
            await self._send_error_message(update_or_query, "Error editing setting.")
    
    async def handle_setting_value_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process user input for setting value"""
        try:
            user_id = update.effective_user.id
            text = update.message.text.strip()
            
            logger.info(f"handle_setting_value_input called for user {user_id} with text: '{text}'")
            
            if user_id not in self.user_sessions:
                logger.warning(f"User {user_id} not in user_sessions")
                return
            
            session = self.user_sessions[user_id]
            logger.info(f"User session: {session}")
            
            if session.get('state') != WAITING_FOR_SETTING_VALUE:
                logger.warning(f"Wrong state: {session.get('state')} != {WAITING_FOR_SETTING_VALUE}")
                return
            
            category = session['category']
            key = session['key']
            setting_config = session['setting_config']
            
            # Handle cancel
            if text.lower() in ['iptal', 'cancel']:
                del self.user_sessions[user_id]
                await update.message.reply_text(
                    "❌ Operation cancelled.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back to Settings", callback_data=f"settings_category_{category}")]
                    ])
                )
                return
            
            # Parse and validate value
            setting_type = setting_config.get('type', 'string')
            
            try:
                if setting_type == 'int':
                    new_value = int(text)
                elif setting_type == 'float':
                    new_value = float(text)
                else:
                    new_value = text
                
            except ValueError:
                await update.message.reply_text(
                    f"❌ Invalid value! {setting_type} type a value.\n\n"
                    f"Try again or type 'cancel' to cancel."
                )
                return
            
            # Validate range
            min_val = setting_config.get('min')
            max_val = setting_config.get('max')
            
            if setting_type in ['int', 'float']:
                if min_val is not None and new_value < min_val:
                    await update.message.reply_text(
                        f"❌ Value too small! Minimum: {min_val}\n\n"
                        f"Try again or type 'cancel' to cancel."
                    )
                    return
                
                if max_val is not None and new_value > max_val:
                    await update.message.reply_text(
                        f"❌ Value too large! Maximum: {max_val}\n\n"
                        f"Try again or type 'cancel' to cancel."
                    )
                    return
            
            # Validate with JSON-based validation
            if not self.settings_manager.validate_setting_value(category, key, new_value):
                await update.message.reply_text(
                    f"❌ Invalid value for {key}! Please check the allowed range/format.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back", callback_data=f"settings_category_{category}")]
                    ])
                )
                del self.user_sessions[user_id]
                return
            
            # Save setting
            success = self.settings_manager.set_setting(category, key, new_value, user_id)
            
            if success:
                description = setting_config.get('description', key)
                restart_required = setting_config.get('restart_required', False)
                
                message = f"✅ **{description}** updated!\n\n"
                message += f"New value: `{new_value}`"
                
                if restart_required:
                    message += "\n\n🔄 **Warning:** Bot must be restarted for this change!"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Settings", callback_data=f"settings_category_{category}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                
                # Apply runtime settings if no restart required
                if not restart_required:
                    logger.info(f"Applying runtime settings for {category}.{key} = {new_value}")
                    success_apply = self.settings_manager.apply_runtime_settings(self.bot.config)
                    if success_apply:
                        logger.info(f"✅ Successfully applied runtime setting change: {category}.{key} = {new_value}")
                    else:
                        logger.warning(f"⚠️ Failed to apply runtime setting change: {category}.{key} = {new_value}")
                        
                    # Force refresh configuration in trade executor and exchange API if exists
                    if hasattr(self.bot, 'exchange_api') and self.bot.exchange_api:
                        try:
                            # Update trade amount in exchange API
                            if category == 'trading' and key == 'trade_amount':
                                self.bot.exchange_api.update_trade_amount(float(new_value))
                                logger.info(f"Updated exchange API trade_amount to {new_value}")
                        except Exception as e:
                            logger.error(f"Error updating exchange API config: {str(e)}")
                else:
                    logger.info(f"Setting {category}.{key} requires restart to take effect")
            else:
                await update.message.reply_text(
                    f"❌ Could not save setting! Please try again.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back to Settings", callback_data=f"settings_category_{category}")]
                    ])
                )
            
            # Clear session
            del self.user_sessions[user_id]
            
        except Exception as e:
            logger.error(f"Error handling setting value input: {str(e)}")
            await update.message.reply_text("❌ An unexpected error occurred!")
    
    async def handle_settings_export(self, update_or_query):
        """Export settings"""
        try:
            exported_settings = self.settings_manager.export_settings()
            
            if not exported_settings:
                message = "📁 **Export Result**\n\nNo custom settings found (all settings at default values)."
            else:
                import json
                settings_json = json.dumps(exported_settings, indent=2, ensure_ascii=False)
                
                message = f"""
📁 **Ayarlar Export Edildi**

```json
{settings_json}
```

You can copy and save this JSON.
To import use `/settings` → Import.
                """
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error exporting settings: {str(e)}")
            await self._send_error_message(update_or_query, "Error exporting settings.")
    
    async def handle_settings_status(self, update_or_query):
        """Ayar durumu raporu"""
        try:
            restart_required = self.settings_manager.get_settings_requiring_restart()
            
            message = "📊 **Ayar Durumu Raporu**\n\n"
            
            # Runtime vs restart required ayarlar
            runtime_count = 0
            restart_count = len(restart_required)
            
            # Count runtime settings
            for category, cat_config in self.settings_config.items():
                settings = cat_config.get('settings', {})
                for key, setting_config in settings.items():
                    if not setting_config.get('restart_required', False):
                        db_key = f"{category}.{key}"
                        if self.settings_manager.db.get_setting(db_key) is not None:
                            runtime_count += 1
            
            message += f"🔄 **Runtime Settings:** {runtime_count} (applied immediately)\n"
            message += f"⚠️ **Restart Required:** {restart_count} (restart required)\n\n"
            
            if restart_required:
                message += "🔄 **Restart Gereken Ayarlar:**\n"
                for setting in restart_required:
                    message += f"• `{setting}`\n"
                message += "\n⚠️ Bot must be restarted for these settings to take effect!"
            else:
                message += "✅ All setting changes are active!"
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing settings status: {str(e)}")
            await self._send_error_message(update_or_query, "Error showing setting status.")
    
    async def handle_reset_category(self, update_or_query, category: str):
        """Reset category settings"""
        try:
            user_id = self._get_user_id(update_or_query)
            
            # Get category configuration from JSON
            cat_config = self.settings_config.get(category)
            if not cat_config:
                await self._send_error_message(update_or_query, f"Category not found: {category}")
                return
            
            settings = cat_config.get('settings', {})
            if not settings:
                await self._send_error_message(update_or_query, f"No settings found for category: {category}")
                return
            
            reset_count = 0
            
            # Reset each setting in the category by deleting from database
            for key in settings.keys():
                try:
                    db_key = f"{category}.{key}"
                    # Delete from database to revert to default
                    query = "DELETE FROM bot_settings WHERE key = ?"
                    rows_affected = self.settings_manager.db.execute_update(query, (db_key,))
                    if rows_affected > 0:
                        reset_count += 1
                        # Clear cache
                        cache_key = f"{category}.{key}"
                        if cache_key in self.settings_manager._cached_settings:
                            del self.settings_manager._cached_settings[cache_key]
                except Exception as e:
                    logger.error(f"Error resetting {category}.{key}: {str(e)}")
            
            category_titles = {
                'trading': 'Trading',
                'technical': 'Teknik Analiz',
                'notifications': 'Bildirim',
                'system': 'Sistem'
            }
            
            category_title = category_titles.get(category, category.title())
            
            message = f"✅ **{category_title} Settings Reset**\n\n"
            message += f"{reset_count} settings returned to default values."
            
            keyboard = [
                [InlineKeyboardButton("📊 View Current Settings", callback_data=f"settings_category_{category}")],
                [InlineKeyboardButton("⬅️ Main Settings", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, message, reply_markup)
            
            # Apply runtime changes
            self.settings_manager.apply_runtime_settings(self.bot.config)
            
        except Exception as e:
            logger.error(f"Error resetting category {category}: {str(e)}")
            await self._send_error_message(update_or_query, f"'{category}' error occurred while resetting.")
    
    # Utility methods
    def _get_user_id(self, update_or_query) -> int:
        """Get user ID from update or callback query"""
        if hasattr(update_or_query, 'callback_query'):
            return update_or_query.callback_query.from_user.id
        elif hasattr(update_or_query, 'effective_user'):
            return update_or_query.effective_user.id
        elif hasattr(update_or_query, 'from_user'):
            return update_or_query.from_user.id
        else:
            return 0
    
    async def _send_or_edit_message(self, update_or_query, text: str, reply_markup=None):
        """Send or edit message utility"""
        try:
            if hasattr(update_or_query, 'callback_query'):
                await update_or_query.callback_query.edit_message_text(
                    text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
                )
            elif hasattr(update_or_query, 'message'):
                await update_or_query.message.reply_text(
                    text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
                )
            else:
                await update_or_query.edit_message_text(
                    text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error sending/editing message: {str(e)}")
    
    async def _send_error_message(self, update_or_query, error_text: str):
        """Send error message utility"""
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_or_edit_message(
            update_or_query, 
            f"❌ **Hata**\n\n{error_text}", 
            reply_markup
        )
