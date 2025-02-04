from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# États de conversation (à importer depuis un fichier central de constantes plus tard si tu veux)
CHOOSING = "CHOOSING"

class UIHandler:
    def __init__(self, config, save_active_users):
        self.CONFIG = config
        self.save_active_users = save_active_users


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
        """Affiche le menu d'accueil"""
        chat_id = update.effective_chat.id
        user = update.effective_user

        # Sauvegarder les informations de l'utilisateur
        if 'active_users' not in context.bot_data:
            context.bot_data['active_users'] = {}
        
        context.bot_data['active_users'][user.id] = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'last_seen': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_active_users(context.bot_data['active_users'])

        # Créer le keyboard de base
        keyboard = [
            [InlineKeyboardButton("📋 MENU", callback_data="show_categories")]
        ]

        # Ajouter le bouton admin si l'utilisateur est administrateur
        if str(update.effective_user.id) in self.CONFIG['admin_ids']:
            keyboard.append([InlineKeyboardButton("🔧 Menu Admin", callback_data="admin")])

        # Ajouter les boutons de contact et canaux
        keyboard.extend([
            [
                InlineKeyboardButton("📞 Contact telegram", url=f"https://t.me/{self.CONFIG['contact_username']}"),
                InlineKeyboardButton("📝 Canal telegram", url="https://t.me/+LT2G6gMsMjY3MWFk"),
            ],
            [InlineKeyboardButton("🥔 Canal potato", url="https://doudlj.org/joinchat/5ZEmn25bOsTR7f-aYdvC0Q")]
        ])

        welcome_text = (
            "🌿 *Bienvenue sur le bot test de DDLAD* 🌿\n\n"
            "Ceci n'est pas le produit final.\n"
            "Ce bot est juste un bot test, pour tester mes conneries dessus.\n\n"
            "📋 Cliquez sur MENU pour voir les catégories"
        )

        try:
            # Vérifier si une image banner est configurée
            if self.CONFIG.get('banner_image'):
                # Si un ancien message banner existe, le supprimer
                if 'banner_message_id' in context.user_data:
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id,
                            message_id=context.user_data['banner_message_id']
                        )
                    except:
                        pass
                
                # Envoyer la nouvelle image banner
                banner_message = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=self.CONFIG['banner_image']
                )
                context.user_data['banner_message_id'] = banner_message.message_id

            # Si c'est un callback_query, éditer le message
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=welcome_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                # Sinon, envoyer un nouveau message
                menu_message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                context.user_data['menu_message_id'] = menu_message.message_id

        except Exception as e:
            print(f"Erreur lors de l'affichage du menu d'accueil: {e}")
            # En cas d'erreur, envoyer au moins le menu basique
            if not update.callback_query:
                menu_message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                context.user_data['menu_message_id'] = menu_message.message_id

        return CHOOSING

class UIHandler:
    def __init__(self, config, save_active_users):
        self.CONFIG = config
        self.save_active_users = save_active_users

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