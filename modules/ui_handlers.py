from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram import InputMediaPhoto
from config.states import CHOOSING, CHOOSING_PRODUCT  # Ajoute les états dont tu as besoin

# États de conversation (à importer depuis un fichier central de constantes plus tard si tu veux)
CHOOSING = "CHOOSING"

class UIHandler:
    def __init__(self, config, save_active_users_callback, catalog, admin_ids):
        self.config = config
        self.save_active_users = save_active_users_callback
        self.catalog = catalog
        self.admin_ids = admin_ids # Ajout de cette ligne

    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Affiche les catégories disponibles"""
        query = update.callback_query
        if query:
            await query.answer()

        # Créer le clavier avec les catégories
        keyboard = []
        for category in self.catalog.keys():
            keyboard.append([InlineKeyboardButton(category, callback_data=f"category_{category}")])
    
        # Ajouter le bouton retour
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="back_to_home")])

        message_text = "📋 *Catégories disponibles*\n\nChoisissez une catégorie :"

        if query:
            await query.edit_message_text(
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        return CHOOSING_PRODUCT

    async def show_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Affiche les produits d'une catégorie"""
        query = update.callback_query
        category = query.data.replace("category_", "")
        
        if category in self.CATALOG:
            products = self.CATALOG[category]
            keyboard = []
            for product in products:
                keyboard.append([InlineKeyboardButton(
                    product['name'], 
                    callback_data=f"product_{category}_{product['name']}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="show_categories")])
            
            await query.edit_message_text(
                f"*{category}*\n\nChoisissez un produit :",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        return CHOOSING

    async def show_home(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Affiche le menu principal"""
        keyboard = [
            [InlineKeyboardButton("🛍 Catalogue", callback_data="show_categories")],
            [InlineKeyboardButton("ℹ️ À propos", callback_data="about")],
            [InlineKeyboardButton("📞 Contact", callback_data="contact")]
        ]
    
        if str(update.effective_user.id) in self.admin_ids:
            keyboard.append([InlineKeyboardButton("🔧 Admin", callback_data="admin")])

        message_text = (
            "🎮 *Bienvenue sur le Bot*\n\n"
            "Choisissez une option ci-dessous :"
        )

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.edit_text(
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        return CHOOSING