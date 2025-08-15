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

# Conversation states for settings
(WAITING_FOR_SETTING_VALUE, WAITING_FOR_CONFIRMATION, 
 WAITING_FOR_CATEGORY_SELECTION, WAITING_FOR_SETTING_SELECTION) = range(4)

class SettingsHandlers:
    """Telegram bot settings command handlers"""
    
    def __init__(self, dynamic_settings_manager, telegram_bot):
        self.settings_manager = dynamic_settings_manager
        self.bot = telegram_bot
        self.user_sessions = {}  # Store user conversation state
        
        logger.info("Settings handlers initialized")
    
    async def handle_settings_main(self, update_or_query, context=None):
        """Main settings menu"""
        try:
            settings_text = """
⚙️ **Bot Settings**

Select a category below to view and modify settings:

🔧 **Available Categories:**
• 💰 **Trading** - Trade amount, risk settings
• 📊 **Technical Analysis** - RSI, ATR parameters  
• 🔔 **Notifications** - Which events to notify
• ⚙️ **System** - General system settings

⚠️ **Note:** Some settings may require restart after changes.
            """
            
            # Category selection keyboard
            keyboard = [
                [
                    InlineKeyboardButton("💰 Trading", callback_data="settings_category_trading"),
                    InlineKeyboardButton("📊 Technical", callback_data="settings_category_technical")
                ],
                [
                    InlineKeyboardButton("🔔 Notifications", callback_data="settings_category_notifications"),
                    InlineKeyboardButton("⚙️ System", callback_data="settings_category_system")
                ],
                [
                    InlineKeyboardButton("📁 Export", callback_data="settings_export"),
                    InlineKeyboardButton("📥 Import", callback_data="settings_import")
                ],
                [
                    InlineKeyboardButton("🔄 Reset to Default", callback_data="settings_reset_all"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, settings_text, reply_markup)
            
        except Exception as e:
            logger.error(f"Error in settings main: {str(e)}")
            await self._send_error_message(update_or_query, "Error loading settings menu.")
    
    async def handle_settings_category(self, update_or_query, category: str):
        """Belirli bir kategori ayarlarını göster"""
        try:
            category_settings = self.settings_manager.get_category_settings(category)
            
            if not category_settings:
                await self._send_error_message(update_or_query, f"Category '{category}' not found!")
                return
            
            # Category title mapping
            category_titles = {
                'trading': '💰 Trading Settings',
                'technical': '📊 Technical Analysis Settings', 
                'notifications': '🔔 Notification Settings',
                'system': '⚙️ System Settings'
            }
            
            title = category_titles.get(category, f"{category.title()} Settings")
            settings_text = f"**{title}**\n\n"
            
            # Show current settings
            for key, setting_info in category_settings.items():
                value = setting_info['value']
                description = setting_info['description']
                setting_type = setting_info['type']
                restart_required = setting_info.get('restart_required', False)
                
                # Format value display
                if setting_type == 'bool':
                    value_display = "✅ Active" if value else "❌ Inactive"
                elif setting_type in ['int', 'float']:
                    min_val = setting_info.get('min_value')
                    max_val = setting_info.get('max_value')
                    range_info = f" ({min_val}-{max_val})" if min_val is not None and max_val is not None else ""
                    value_display = f"{value}{range_info}"
                else:
                    value_display = str(value)
                
                restart_indicator = " 🔄" if restart_required else ""
                
                settings_text += f"• **{description}**{restart_indicator}\n"
                settings_text += f"  Value: `{value_display}`\n\n"
            
            if any(s.get('restart_required', False) for s in category_settings.values()):
                settings_text += "\n🔄 = Requires restart after change"
            
            # Create keyboard for individual setting changes
            keyboard = []
            
            # Setting buttons (max 2 per row)
            setting_buttons = []
            for key, setting_info in category_settings.items():
                button_text = setting_info['description'][:25] + "..." if len(setting_info['description']) > 25 else setting_info['description']
                setting_buttons.append(
                    InlineKeyboardButton(
                        f"✏️ {button_text}", 
                        callback_data=f"settings_edit_{category}_{key}"
                    )
                )
            
            # Group buttons in rows of 2
            for i in range(0, len(setting_buttons), 2):
                row = setting_buttons[i:i+2]
                keyboard.append(row)
            
            # Control buttons
            keyboard.extend([
                [
                    InlineKeyboardButton("🔄 Reset Category", callback_data=f"settings_reset_category_{category}"),
                    InlineKeyboardButton("📊 Status", callback_data="settings_status")
                ],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data="settings_main"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, settings_text, reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing category {category}: {str(e)}")
            await self._send_error_message(update_or_query, f"'{category}' error loading settings.")
    
    async def handle_setting_edit(self, update_or_query, category: str, key: str):
        """Belirli bir ayarı düzenle"""
        try:
            category_settings = self.settings_manager.get_category_settings(category)
            
            if key not in category_settings:
                await self._send_error_message(update_or_query, f"Setting not found: {category}.{key}")
                return
            
            setting_info = category_settings[key]
            current_value = setting_info['value']
            description = setting_info['description']
            setting_type = setting_info['type']
            min_val = setting_info.get('min_value')
            max_val = setting_info.get('max_value')
            restart_required = setting_info.get('restart_required', False)
            
            # Create edit interface based on setting type
            if setting_type == 'bool':
                # Boolean toggle
                new_value = not current_value
                success = self.settings_manager.set_setting(
                    category, key, new_value, 
                    user_id=self._get_user_id(update_or_query)
                )
                
                if success:
                    status = "✅ Aktif" if new_value else "❌ Pasif"
                    message = f"✅ **{description}** updated!\n\nNew value: {status}"
                    
                    if restart_required:
                        message += "\n\n🔄 **Uyarı:** Bot must be restarted for this change!"
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
                    'setting_info': setting_info
                }
                
        except Exception as e:
            logger.error(f"Error editing setting {category}.{key}: {str(e)}")
            await self._send_error_message(update_or_query, "Error editing setting.")
    
    async def handle_setting_value_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kullanıcının girdiği setting değerini işle"""
        try:
            user_id = update.effective_user.id
            text = update.message.text.strip()
            
            if user_id not in self.user_sessions:
                return
            
            session = self.user_sessions[user_id]
            
            if session.get('state') != WAITING_FOR_SETTING_VALUE:
                return
            
            category = session['category']
            key = session['key']
            setting_info = session['setting_info']
            
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
            setting_type = setting_info['type']
            
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
            min_val = setting_info.get('min_value')
            max_val = setting_info.get('max_value')
            
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
            
            # Save setting
            success = self.settings_manager.set_setting(category, key, new_value, user_id)
            
            if success:
                description = setting_info['description']
                restart_required = setting_info.get('restart_required', False)
                
                message = f"✅ **{description}** updated!\n\n"
                message += f"New value: `{new_value}`"
                
                if restart_required:
                    message += "\n\n🔄 **Uyarı:** Bot must be restarted for this change!"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Settings", callback_data=f"settings_category_{category}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                
                # Apply runtime settings if no restart required
                if not restart_required:
                    self.settings_manager.apply_runtime_settings(self.bot.config)
                    logger.info(f"Applied runtime setting change: {category}.{key} = {new_value}")
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
        """Ayarları export et"""
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
            for category in ['trading', 'technical', 'notifications', 'system']:
                category_settings = self.settings_manager.get_category_settings(category)
                for key, setting_info in category_settings.items():
                    if not setting_info.get('restart_required', False):
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
        """Kategori ayarlarını sıfırla"""
        try:
            user_id = self._get_user_id(update_or_query)
            category_settings = self.settings_manager.get_category_settings(category)
            
            if not category_settings:
                await self._send_error_message(update_or_query, f"Category not found: {category}")
                return
            
            reset_count = 0
            
            for key in category_settings.keys():
                if self.settings_manager.reset_setting(category, key, user_id):
                    reset_count += 1
            
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
