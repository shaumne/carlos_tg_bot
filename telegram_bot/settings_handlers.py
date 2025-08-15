#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot Settings Handlers
Kullanıcıların bot üzerinden ayarları değiştirmesini sağlayan handler'lar
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
        """Ana settings menüsü"""
        try:
            settings_text = """
⚙️ **Bot Ayarları**

Aşağıdaki kategorilerden birini seçerek ayarları görüntüleyip değiştirebilirsiniz:

🔧 **Mevcut Kategoriler:**
• 💰 **Trading** - İşlem miktarı, risk ayarları
• 📊 **Teknik Analiz** - RSI, ATR parametreleri  
• 🔔 **Bildirimler** - Hangi olaylar bildirilsin
• ⚙️ **Sistem** - Genel sistem ayarları

⚠️ **Not:** Bazı ayarlar değişiklik sonrası yeniden başlatma gerektirebilir.
            """
            
            # Category selection keyboard
            keyboard = [
                [
                    InlineKeyboardButton("💰 Trading", callback_data="settings_category_trading"),
                    InlineKeyboardButton("📊 Teknik", callback_data="settings_category_technical")
                ],
                [
                    InlineKeyboardButton("🔔 Bildirimler", callback_data="settings_category_notifications"),
                    InlineKeyboardButton("⚙️ Sistem", callback_data="settings_category_system")
                ],
                [
                    InlineKeyboardButton("📁 Export", callback_data="settings_export"),
                    InlineKeyboardButton("📥 Import", callback_data="settings_import")
                ],
                [
                    InlineKeyboardButton("🔄 Varsayılana Sıfırla", callback_data="settings_reset_all"),
                    InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, settings_text, reply_markup)
            
        except Exception as e:
            logger.error(f"Error in settings main: {str(e)}")
            await self._send_error_message(update_or_query, "Ayarlar menüsü yüklenirken hata oluştu.")
    
    async def handle_settings_category(self, update_or_query, category: str):
        """Belirli bir kategori ayarlarını göster"""
        try:
            category_settings = self.settings_manager.get_category_settings(category)
            
            if not category_settings:
                await self._send_error_message(update_or_query, f"'{category}' kategorisi bulunamadı!")
                return
            
            # Category title mapping
            category_titles = {
                'trading': '💰 Trading Ayarları',
                'technical': '📊 Teknik Analiz Ayarları', 
                'notifications': '🔔 Bildirim Ayarları',
                'system': '⚙️ Sistem Ayarları'
            }
            
            title = category_titles.get(category, f"{category.title()} Ayarları")
            settings_text = f"**{title}**\n\n"
            
            # Show current settings
            for key, setting_info in category_settings.items():
                value = setting_info['value']
                description = setting_info['description']
                setting_type = setting_info['type']
                restart_required = setting_info.get('restart_required', False)
                
                # Format value display
                if setting_type == 'bool':
                    value_display = "✅ Aktif" if value else "❌ Pasif"
                elif setting_type in ['int', 'float']:
                    min_val = setting_info.get('min_value')
                    max_val = setting_info.get('max_value')
                    range_info = f" ({min_val}-{max_val})" if min_val is not None and max_val is not None else ""
                    value_display = f"{value}{range_info}"
                else:
                    value_display = str(value)
                
                restart_indicator = " 🔄" if restart_required else ""
                
                settings_text += f"• **{description}**{restart_indicator}\n"
                settings_text += f"  Değer: `{value_display}`\n\n"
            
            if any(s.get('restart_required', False) for s in category_settings.values()):
                settings_text += "\n🔄 = Değişiklik sonrası yeniden başlatma gerektirir"
            
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
                    InlineKeyboardButton("🔄 Kategori Sıfırla", callback_data=f"settings_reset_category_{category}"),
                    InlineKeyboardButton("📊 Genel Durum", callback_data="settings_status")
                ],
                [
                    InlineKeyboardButton("⬅️ Geri", callback_data="settings_main"),
                    InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
                ]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, settings_text, reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing category {category}: {str(e)}")
            await self._send_error_message(update_or_query, f"'{category}' ayarları yüklenirken hata oluştu.")
    
    async def handle_setting_edit(self, update_or_query, category: str, key: str):
        """Belirli bir ayarı düzenle"""
        try:
            category_settings = self.settings_manager.get_category_settings(category)
            
            if key not in category_settings:
                await self._send_error_message(update_or_query, f"Ayar bulunamadı: {category}.{key}")
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
                    message = f"✅ **{description}** güncellendi!\n\nYeni değer: {status}"
                    
                    if restart_required:
                        message += "\n\n🔄 **Uyarı:** Bu değişiklik için bot yeniden başlatılmalı!"
                else:
                    message = f"❌ **{description}** güncellenemedi!"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Geri", callback_data=f"settings_category_{category}")]
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
✏️ **{description}** Düzenle

**Mevcut değer:** `{current_value}`
**Tip:** {setting_type} {range_info}

Yeni değeri yazın veya iptal etmek için "iptal" yazın.
                """
                
                keyboard = [
                    [InlineKeyboardButton("❌ İptal", callback_data=f"settings_category_{category}")]
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
            await self._send_error_message(update_or_query, "Ayar düzenlenirken hata oluştu.")
    
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
                    "❌ İşlem iptal edildi.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Ayarlara Dön", callback_data=f"settings_category_{category}")]
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
                    f"❌ Geçersiz değer! {setting_type} tipinde bir değer girin.\n\n"
                    f"Tekrar deneyin veya iptal etmek için 'iptal' yazın."
                )
                return
            
            # Validate range
            min_val = setting_info.get('min_value')
            max_val = setting_info.get('max_value')
            
            if setting_type in ['int', 'float']:
                if min_val is not None and new_value < min_val:
                    await update.message.reply_text(
                        f"❌ Değer çok küçük! Minimum: {min_val}\n\n"
                        f"Tekrar deneyin veya iptal etmek için 'iptal' yazın."
                    )
                    return
                
                if max_val is not None and new_value > max_val:
                    await update.message.reply_text(
                        f"❌ Değer çok büyük! Maksimum: {max_val}\n\n"
                        f"Tekrar deneyin veya iptal etmek için 'iptal' yazın."
                    )
                    return
            
            # Save setting
            success = self.settings_manager.set_setting(category, key, new_value, user_id)
            
            if success:
                description = setting_info['description']
                restart_required = setting_info.get('restart_required', False)
                
                message = f"✅ **{description}** güncellendi!\n\n"
                message += f"Yeni değer: `{new_value}`"
                
                if restart_required:
                    message += "\n\n🔄 **Uyarı:** Bu değişiklik için bot yeniden başlatılmalı!"
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Ayarlara Dön", callback_data=f"settings_category_{category}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                
                # Apply runtime settings if no restart required
                if not restart_required:
                    self.settings_manager.apply_runtime_settings(self.bot.config)
                    logger.info(f"Applied runtime setting change: {category}.{key} = {new_value}")
            else:
                await update.message.reply_text(
                    f"❌ Ayar kaydedilemedi! Lütfen tekrar deneyin.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Ayarlara Dön", callback_data=f"settings_category_{category}")]
                    ])
                )
            
            # Clear session
            del self.user_sessions[user_id]
            
        except Exception as e:
            logger.error(f"Error handling setting value input: {str(e)}")
            await update.message.reply_text("❌ Beklenmedik bir hata oluştu!")
    
    async def handle_settings_export(self, update_or_query):
        """Ayarları export et"""
        try:
            exported_settings = self.settings_manager.export_settings()
            
            if not exported_settings:
                message = "📁 **Export Sonucu**\n\nHerhangi bir özel ayar bulunamadı (tüm ayarlar varsayılan değerlerde)."
            else:
                import json
                settings_json = json.dumps(exported_settings, indent=2, ensure_ascii=False)
                
                message = f"""
📁 **Ayarlar Export Edildi**

```json
{settings_json}
```

Bu JSON'ı kopyalayıp saklayabilirsiniz.
Import etmek için `/settings` → Import kullanın.
                """
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Ayarlara Dön", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error exporting settings: {str(e)}")
            await self._send_error_message(update_or_query, "Ayarlar export edilirken hata oluştu.")
    
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
            
            message += f"🔄 **Runtime Ayarlar:** {runtime_count} (anında uygulanır)\n"
            message += f"⚠️ **Restart Gereken:** {restart_count} (yeniden başlatma gerekir)\n\n"
            
            if restart_required:
                message += "🔄 **Restart Gereken Ayarlar:**\n"
                for setting in restart_required:
                    message += f"• `{setting}`\n"
                message += "\n⚠️ Bu ayarların etkili olması için bot yeniden başlatılmalı!"
            else:
                message += "✅ Tüm ayar değişiklikleri aktif!"
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Ayarlara Dön", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing settings status: {str(e)}")
            await self._send_error_message(update_or_query, "Ayar durumu gösterilirken hata oluştu.")
    
    async def handle_reset_category(self, update_or_query, category: str):
        """Kategori ayarlarını sıfırla"""
        try:
            user_id = self._get_user_id(update_or_query)
            category_settings = self.settings_manager.get_category_settings(category)
            
            if not category_settings:
                await self._send_error_message(update_or_query, f"Kategori bulunamadı: {category}")
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
            
            message = f"✅ **{category_title} Ayarları Sıfırlandı**\n\n"
            message += f"{reset_count} ayar varsayılan değerlere döndürüldü."
            
            keyboard = [
                [InlineKeyboardButton("📊 Güncel Ayarları Gör", callback_data=f"settings_category_{category}")],
                [InlineKeyboardButton("⬅️ Ana Ayarlar", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_or_edit_message(update_or_query, message, reply_markup)
            
            # Apply runtime changes
            self.settings_manager.apply_runtime_settings(self.bot.config)
            
        except Exception as e:
            logger.error(f"Error resetting category {category}: {str(e)}")
            await self._send_error_message(update_or_query, f"'{category}' sıfırlanırken hata oluştu.")
    
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
            [InlineKeyboardButton("⬅️ Ayarlara Dön", callback_data="settings_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_or_edit_message(
            update_or_query, 
            f"❌ **Hata**\n\n{error_text}", 
            reply_markup
        )
