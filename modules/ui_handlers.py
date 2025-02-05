from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram import InputMediaPhoto

# États de conversation (à importer depuis un fichier central de constantes plus tard si tu veux)
CHOOSING = "CHOOSING"

class UIHandler:
    def __init__(self, config, save_active_users, catalog):  # Ajout de catalog
        self.CONFIG = config
        self.save_active_users = save_active_users
        self.CATALOG = catalog  # Ajout de cette ligne

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
        """Affiche le menu principal avec la bannière"""
        # Créer le clavier
        keyboard = [
            [InlineKeyboardButton("🛍 Catalogue", callback_data="show_categories")],
            [InlineKeyboardButton("ℹ️ À propos", callback_data="about")],
            [InlineKeyboardButton("📞 Contact", callback_data="contact")]
        ]
    
        # Ajouter le bouton admin si l'utilisateur est admin
        if str(update.effective_user.id) in self.admin_ids:
            keyboard.append([InlineKeyboardButton("🔧 Admin", callback_data="admin")])

        # Message avec mention de la bannière
        message_text = (
            "🎮 *Bienvenue sur le Bot*\n\n"
            "Choisissez une option ci-dessous :"
        )

        # Si c'est un callback_query (retour au menu)
        if update.callback_query:
            # Modifier le message existant avec la nouvelle photo et le nouveau texte
            with open('assets/banner.jpg', 'rb') as photo:
                await update.callback_query.message.edit_media(
                    media=InputMediaPhoto(
                        media=photo,
                        caption=message_text,
                        parse_mode='Markdown'
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            await update.callback_query.answer()
        # Si c'est un nouveau message (commande /start)
        else:
            # Envoyer un nouveau message avec la photo
            with open('assets/banner.jpg', 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=message_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

        return CHOOSING