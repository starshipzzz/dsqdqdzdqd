import json
import logging
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
        keyboard = []
    
        # Charger les catégories depuis le fichier JSON
        try:
            with open('data/categories.json', 'r', encoding='utf-8') as f:
                categories = json.load(f)
            
            # Créer les boutons pour chaque catégorie
            for category in categories:
                keyboard.append([InlineKeyboardButton(
                    category['name'], 
                    callback_data=f"category_{category['id']}"
                )])
        except FileNotFoundError:
            keyboard = []
    
        # Ajouter le bouton retour
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="back_to_home")])
    
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.delete()
            await update.callback_query.message.reply_text(
                "🗂 *Catégories disponibles*\n\nChoisissez une catégorie :",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "🗂 *Catégories disponibles*\n\nChoisissez une catégorie :",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
        return CHOOSING

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

    async def show_product_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Affiche les détails d'un produit"""
        query = update.callback_query
        product_id = query.data.replace("product_", "")
        
        try:
            # Charger le produit depuis le fichier JSON
            with open('data/products.json', 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            product = next((p for p in products if p['id'] == product_id), None)
            
            if product:
                media = product['media']
                if media and len(media) > 0:
                    # S'il y a des médias, envoyer le premier
                    first_media = media[0]
                    keyboard = [
                        [InlineKeyboardButton("🔙 Retour au catalogue", callback_data="show_categories")]
                    ]
                    
                    message_text = (
                        f"*{product['name']}*\n\n"
                        f"{product['description']}\n\n"
                        f"💰 Prix : {product['price']} €"
                    )
                    
                    if first_media['type'] == 'photo':
                        await query.message.delete()
                        await query.message.reply_photo(
                            photo=first_media['file_id'],
                            caption=message_text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                    elif first_media['type'] == 'video':
                        await query.message.delete()
                        await query.message.reply_video(
                            video=first_media['file_id'],
                            caption=message_text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                else:
                    # Si pas de média, envoyer juste le texte
                    keyboard = [[InlineKeyboardButton("🔙 Retour au catalogue", callback_data="show_categories")]]
                    await query.message.edit_text(
                        f"*{product['name']}*\n\n"
                        f"{product['description']}\n\n"
                        f"💰 Prix : {product['price']} €",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
            else:
                keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="show_categories")]]
                await query.message.edit_text(
                    "Produit non trouvé.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except FileNotFoundError:
            keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="show_categories")]]
            await query.message.edit_text(
                "Erreur : fichier produits non trouvé.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        await query.answer()
        return CHOOSING

    async def show_home(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Affiche le menu principal"""
        try:
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

            try:
                with open('assets/banner.jpg', 'rb') as photo:
                    if update.callback_query:
                        await update.callback_query.message.delete()
                        message = await update.callback_query.message.reply_photo(
                            photo=photo,
                            caption=message_text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                        await update.callback_query.answer()
                    else:
                        await update.message.reply_photo(
                            photo=photo,
                            caption=message_text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
            except FileNotFoundError:
                # Si la bannière n'est pas trouvée, envoyer juste le texte
                if update.callback_query:
                    await update.callback_query.message.edit_text(
                        text=message_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                    await update.callback_query.answer()
                else:
                    await update.message.reply_text(
                        text=message_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )

            return CHOOSING
        except Exception as e:
            logging.error(f"Erreur dans show_home: {str(e)}")

    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Affiche le menu administrateur"""
        user_id = str(update.effective_user.id)
        keyboard = []
        message_text = ""

        # Vérifie si l'utilisateur est admin
        if user_id not in self.admin_ids:
            keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_home")]]
            message_text = "⛔️ Accès refusé. Vous n'avez pas les droits d'administration."
        else:
            # Menu admin pour les utilisateurs autorisés
            keyboard = [
                [InlineKeyboardButton("➕ Ajouter un produit", callback_data="add_product")],
                [InlineKeyboardButton("✏️ Modifier un produit", callback_data="edit_product")],
                [InlineKeyboardButton("❌ Supprimer un produit", callback_data="remove_product")],
                [InlineKeyboardButton("📁 Ajouter une catégorie", callback_data="add_category")],
                [InlineKeyboardButton("🗑 Supprimer une catégorie", callback_data="remove_category")],
                [InlineKeyboardButton("🔐 Gérer les accès", callback_data="manage_access")],
                [InlineKeyboardButton("📢 Message général", callback_data="broadcast")],
                [InlineKeyboardButton("🔙 Retour", callback_data="back_to_home")]
            ]
            message_text = "🔧 *Menu Administrateur*\n\nQue souhaitez-vous faire ?"

        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.message.delete()
            except:
                pass
            await update.callback_query.message.reply_text(
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

        return CHOOSING if user_id in self.admin_ids else CHOOSING