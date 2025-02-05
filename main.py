﻿import json
import logging
import asyncio
import shutil
import os
import pytz
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ConversationHandler
)

from config.states import *  # Importe tous les états
from modules.ui_handlers import UIHandler
from modules.access_control import AccessControl

os.makedirs('data', exist_ok=True)
os.makedirs('config', exist_ok=True)

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# États de conversation
CHOOSING = "CHOOSING"
CHOOSE_CATEGORY = "CHOOSE_CATEGORY"
CHOOSING_PRODUCT = "CHOOSING_PRODUCT"
CHOOSING_PRODUCT_TO_REMOVE = "CHOOSING_PRODUCT_TO_REMOVE"
CHOOSING_PRODUCT_TO_EDIT = "CHOOSING_PRODUCT_TO_EDIT"  # Ajout de cette constante manquante
WAITING_CATEGORY_NAME = "WAITING_CATEGORY_NAME"
WAITING_PRODUCT_NAME = "WAITING_PRODUCT_NAME"
WAITING_PRODUCT_PRICE = "WAITING_PRODUCT_PRICE"
WAITING_PRODUCT_DESCRIPTION = "WAITING_PRODUCT_DESCRIPTION"
WAITING_PRODUCT_MEDIA = "WAITING_PRODUCT_MEDIA"
WAITING_PRODUCT_CATEGORY = "WAITING_PRODUCT_CATEGORY"
SELECTING_CATEGORY = "SELECTING_CATEGORY"
SELECTING_CATEGORY_TO_DELETE = "SELECTING_CATEGORY_TO_DELETE"
SELECTING_PRODUCT_TO_DELETE = "SELECTING_PRODUCT_TO_DELETE"
SELECTING_PRODUCT_TO_EDIT = "SELECTING_PRODUCT_TO_EDIT"
WAITING_CONTACT_USERNAME = "WAITING_CONTACT_USERNAME"
EDITING_PRODUCT_FIELD = "EDITING_PRODUCT_FIELD"
WAITING_NEW_VALUE = "WAITING_NEW_VALUE"
WAITING_BROADCAST_MESSAGE = "WAITING_BROADCAST_MESSAGE"
CONFIRM_ADD_PRODUCT = "CONFIRM_ADD_PRODUCT"
WAITING_ACCESS_CODE = "WAITING_ACCESS_CODE"
WAITING_NEW_NAME = "WAITING_NEW_NAME"
WAITING_NEW_DESCRIPTION = "WAITING_NEW_DESCRIPTION"
WAITING_NEW_PRICE = "WAITING_NEW_PRICE"
WAITING_NEW_MEDIA = "WAITING_NEW_MEDIA"
WAITING_NEW_CATEGORY = "WAITING_NEW_CATEGORY"
EDITING_PRODUCT = "EDITING_PRODUCT"


# 4. Définition des fonctions utilitaires
def save_catalog():
    """Sauvegarde le catalogue dans le fichier"""
    try:
        with open(CONFIG['catalog_file'], 'w', encoding='utf-8') as f:
            json.dump(CATALOG, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du catalogue : {e}")

def load_catalog():
    """Charge le catalogue depuis le fichier"""
    try:
        with open(CONFIG['catalog_file'], 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config():
    """Sauvegarde la configuration dans le fichier"""
    try:
        with open('config/config.json', 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la configuration : {e}")

def save_active_users(active_users):
    """Sauvegarde la liste des utilisateurs actifs"""
    try:
        with open('data/active_users.json', 'w', encoding='utf-8') as f:
            json.dump(active_users, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des utilisateurs actifs : {e}")

def load_active_users():
    """Charge la liste des utilisateurs actifs"""
    try:
        with open('data/active_users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Charger la configuration
try:
    with open('config/config.json', 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
        TOKEN = CONFIG['token']
        ADMIN_IDS = CONFIG['admin_ids']
except FileNotFoundError:
    print("Erreur: Le fichier config.json n'a pas été trouvé!")
    exit(1)
except KeyError as e:
    print(f"Erreur: La clé {e} est manquante dans le fichier config.json!")
    exit(1)

# Charger le catalogue avant d'initialiser ui_handler
CATALOG = load_catalog()
ACTIVE_USERS = load_active_users()

from modules.ui_handlers import UIHandler
from modules.access_control import AccessControl

# Initialiser les modules dans le bon ordre
ui_handler = UIHandler(CONFIG, save_active_users, CATALOG, ADMIN_IDS)  # Ajout de ADMIN_IDS
access_control = AccessControl(CONFIG, save_config, ADMIN_IDS)
access_control.set_default_callback(ui_handler.show_home)

# Variables globales pour les statistiques
STATS_CACHE = None
LAST_CACHE_UPDATE = None

def save_active_users(users_data):
    """Sauvegarde les données des utilisateurs actifs dans un fichier"""
    try:
        with open('data/active_users.json', 'w', encoding='utf-8') as f:
            # Convertir les IDs en strings pour le JSON
            data = {str(user_id): info for user_id, info in users_data.items()}
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des utilisateurs actifs: {e}")

def load_active_users():
    """Charge les données des utilisateurs actifs depuis le fichier"""
    try:
        with open('data/active_users.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):  # Ancien format (liste d'IDs)
                # Convertir en nouveau format
                return {int(user_id): {
                    'username': None,
                    'first_name': None,
                    'last_name': None,
                    'last_seen': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                } for user_id in data}
            else:  # Nouveau format (dictionnaire)
                return {int(k): v for k, v in data.items()}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Erreur lors du chargement des utilisateurs actifs: {e}")
        return {}

# Fonctions de gestion du catalogue

def save_catalog(catalog):
    with open(CONFIG['catalog_file'], 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)

def clean_stats():
    """Nettoie les statistiques des produits et catégories qui n'existent plus"""
    if 'stats' not in CATALOG:
        return
    
    stats = CATALOG['stats']
    
    # Nettoyer les vues par catégorie
    if 'category_views' in stats:
        categories_to_remove = []
        for category in stats['category_views']:
            if category not in CATALOG or category == 'stats':
                categories_to_remove.append(category)
        
        for category in categories_to_remove:
            del stats['category_views'][category]
            print(f"🧹 Suppression des stats de la catégorie: {category}")

    # Nettoyer les vues par produit
    if 'product_views' in stats:
        categories_to_remove = []
        for category in stats['product_views']:
            if category not in CATALOG or category == 'stats':
                categories_to_remove.append(category)
                continue
            
            products_to_remove = []
            existing_products = [p['name'] for p in CATALOG[category]]
            
            for product_name in stats['product_views'][category]:
                if product_name not in existing_products:
                    products_to_remove.append(product_name)
            
            # Supprimer les produits qui n'existent plus
            for product in products_to_remove:
                del stats['product_views'][category][product]
                print(f"🧹 Suppression des stats du produit: {product} dans {category}")
            
            # Si la catégorie est vide après nettoyage, la marquer pour suppression
            if not stats['product_views'][category]:
                categories_to_remove.append(category)
        
        # Supprimer les catégories vides
        for category in categories_to_remove:
            if category in stats['product_views']:
                del stats['product_views'][category]

    # Mettre à jour la date de dernière modification
    stats['last_updated'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    save_catalog(CATALOG)

def get_stats():
    global STATS_CACHE, LAST_CACHE_UPDATE
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Si le cache existe et a moins de 30 secondes
    if STATS_CACHE and LAST_CACHE_UPDATE and (current_time - LAST_CACHE_UPDATE).seconds < 30:
        return STATS_CACHE
        
    # Sinon, lire le fichier et mettre à jour le cache
    STATS_CACHE = load_catalog()['stats']
    LAST_CACHE_UPDATE = current_time
    return STATS_CACHE

def save_active_users(users_data):
    """Sauvegarde les données des utilisateurs actifs dans un fichier"""
    try:
        with open('data/active_users.json', 'w', encoding='utf-8') as f:
            # Convertir les IDs en strings pour le JSON
            data = {str(user_id): info for user_id, info in users_data.items()}
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des utilisateurs actifs: {e}")

def load_active_users():
    """Charge les données des utilisateurs actifs depuis le fichier"""
    try:
        with open('data/active_users.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):  # Ancien format (liste d'IDs)
                # Convertir en nouveau format
                return {int(user_id): {
                    'username': None,
                    'first_name': None,
                    'last_name': None,
                    'last_seen': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                } for user_id in data}
            else:  # Nouveau format (dictionnaire)
                return {int(k): v for k, v in data.items()}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Erreur lors du chargement des utilisateurs actifs: {e}")
        return {}

def backup_data():
    """Crée une sauvegarde des fichiers de données"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Backup config.json
    if os.path.exists("config/config.json"):
        shutil.copy2("config/config.json", f"{backup_dir}/config_{timestamp}.json")
    
    # Backup catalog.json
    if os.path.exists("config/catalog.json"):
        shutil.copy2("config/catalog.json", f"{backup_dir}/catalog_{timestamp}.json")

def print_catalog_debug():
    """Fonction de debug pour afficher le contenu du catalogue"""
    for category, products in CATALOG.items():
        if category != 'stats':
            print(f"\nCatégorie: {category}")
            for product in products:
                print(f"  Produit: {product['name']}")
                if 'media' in product:
                    print(f"    Médias ({len(product['media'])}): {product['media']}")

# Fonctions de base
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Point d'entrée du bot"""
    has_access = await access_control.check_access(update, context)
    if has_access:
        return await ui_handler.show_home(update, context)
    return WAITING_ACCESS_CODE
    
    # Sauvegarder les informations de l'utilisateur
    context.bot_data['active_users'][user.id] = {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'last_seen': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_active_users(context.bot_data['active_users'])
    # Supprimer le message /start
    await update.message.delete()
    
    # Supprimer les anciens messages si nécessaire
    if 'menu_message_id' in context.user_data:
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=context.user_data['menu_message_id']
            )
        except:
            pass
    
    # Nouveau clavier simplifié pour l'accueil
    keyboard = [
        [InlineKeyboardButton("📋 MENU", callback_data="show_categories")]
    ]

    # Ajouter le bouton admin si l'utilisateur est administrateur
    if str(update.effective_user.id) in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔧 Menu Admin", callback_data="admin")])

    # Ajouter les boutons de contact et canaux
    keyboard.extend([
        [
            InlineKeyboardButton("📞 Contact telegram", url=f"https://t.me/{CONFIG['contact_username']}"),
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
        if CONFIG.get('banner_image'):
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
                photo=CONFIG['banner_image']
            )
            context.user_data['banner_message_id'] = banner_message.message_id

        # Envoyer le menu d'accueil
        menu_message = await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        context.user_data['menu_message_id'] = menu_message.message_id
        
    except Exception as e:
        print(f"Erreur lors du démarrage: {e}")
        # En cas d'erreur, envoyer au moins le menu
        menu_message = await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        context.user_data['menu_message_id'] = menu_message.message_id
    
    return CHOOSING


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la page À propos"""
    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_home")]]
    message_text = (
        "*📌 À propos*\n\n"
        "Ce bot vous permet de :\n"
        "• Consulter notre catalogue de produits\n"
        "• Explorer différentes catégories\n"
        "• Voir les détails des produits"
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.delete()
        await update.callback_query.message.reply_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    return CHOOSING

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la page Contact"""
    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_home")]]
    message_text = (
        "*📞 Contact*\n\n"
        "Pour nous contacter :\n"
        "• Email : ton@email.com\n"
        "• Telegram : @ton_username\n"
        "• Site web : ton-site.com"
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.delete()
        await update.callback_query.message.reply_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    return CHOOSING

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'accès au menu administrateur"""
    user_id = str(update.effective_user.id)
    keyboard = []
    message_text = ""  # Initialisation de message_text
    
    # Vérifie si l'utilisateur a déjà un accès administrateur
    if user_id not in ADMIN_IDS and not access_control.has_access(user_id):
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_home")]]
        message_text = "⛔️ Accès refusé. Veuillez entrer le code d'accès :"
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

    return WAITING_ACCESS_CODE if user_id not in ADMIN_IDS and not access_control.has_access(user_id) else CHOOSING

async def handle_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la sélection de catégorie pour un produit"""
    category_name = update.message.text
    if category_name in CATALOG:
        context.user_data['temp_product_category'] = category_name
        await update.message.reply_text(
            "📝 Veuillez entrer le nom du produit:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Annuler", callback_data="cancel_add_product")
            ]])
        )
        return WAITING_PRODUCT_NAME
    else:
        await update.message.reply_text(
            "❌ Cette catégorie n'existe pas. Veuillez choisir une catégorie valide ou annuler."
        )
        return WAITING_PRODUCT_CATEGORY

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Annule et termine la conversation."""
    await update.message.reply_text(
        "Opération annulée. Tapez /start pour recommencer."
    )
    return ConversationHandler.END

async def finish_adding_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Termine l'ajout de médias et sauvegarde le produit"""
    query = update.callback_query
    await query.answer()
    
    category = context.user_data.get('temp_product_category')
    if not category:
        await query.message.edit_text("Une erreur est survenue. Veuillez recommencer.")
        return await show_admin_menu(update, context)
    
    if 'temp_product_media' not in context.user_data:
        context.user_data['temp_product_media'] = []
    
    new_product = {
        'name': context.user_data.get('temp_product_name'),
        'price': context.user_data.get('temp_product_price'),
        'description': context.user_data.get('temp_product_description'),
        'media': context.user_data.get('temp_product_media')
    }
    
    if category not in CATALOG:
        CATALOG[category] = []
    
    CATALOG[category].append(new_product)
    save_catalog(CATALOG)
    
    await query.message.edit_text(
        "✅ Produit ajouté avec succès !",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Retour au menu", callback_data="admin")
        ]])
    )
    
    context.user_data.clear()
    return CHOOSING

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'ajout d'un nouveau produit"""
    query = update.callback_query
    await query.answer()
    
    # Afficher les catégories disponibles
    keyboard = []
    for category in CATALOG.keys():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"select_category_{category}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data="cancel_add_product")])
    
    await query.edit_message_text(
        "📝 Choisissez une catégorie pour le nouveau produit :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_CATEGORY

async def cancel_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule l'ajout d'un produit"""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    return await show_admin_menu(update, context)

async def handle_product_category_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la sélection de catégorie via bouton"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("select_category_", "")
    context.user_data['temp_product_category'] = category
    
    await query.message.edit_text(
        "📝 Veuillez entrer le nom du nouveau produit:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Annuler", callback_data="cancel_add_product")
        ]])
    )
    return WAITING_PRODUCT_NAME

async def confirm_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirme l'ajout d'un produit"""
    query = update.callback_query
    await query.answer()
    
    category = context.user_data.get('temp_product_category')
    if not category:
        return await show_admin_menu(update, context)

    new_product = {
        'name': context.user_data.get('temp_product_name'),
        'price': context.user_data.get('temp_product_price'),
        'description': context.user_data.get('temp_product_description'),
        'media': context.user_data.get('temp_product_media', [])
    }

    if category not in CATALOG:
        CATALOG[category] = []
    CATALOG[category].append(new_product)
    save_catalog(CATALOG)
    
    await query.message.edit_text(
        "✅ Produit ajouté avec succès !",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Retour au menu", callback_data="admin")
        ]])
    )
    
    context.user_data.clear()
    return CHOOSING

async def remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la suppression d'un produit"""
    query = update.callback_query
    await query.answer()
    
    # Créer le clavier avec tous les produits
    keyboard = []
    for category, products in CATALOG.items():
        for product in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"{product['name']} ({category})", 
                    callback_data=f"remove_product_{category}_{product['name']}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data="cancel_remove_product")])
    
    await query.edit_message_text(
        "🗑 Sélectionnez le produit à supprimer :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_PRODUCT_TO_DELETE

async def confirm_remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirme la suppression d'un produit"""
    query = update.callback_query
    await query.answer()
    
    try:
        _, category, product_name = query.data.replace("remove_product_", "").split("_", 2)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Oui, supprimer", 
                    callback_data=f"really_remove_product_{category}_{product_name}"),
                InlineKeyboardButton("❌ Non, annuler", 
                    callback_data="cancel_remove_product")
            ]
        ]
        
        await query.message.edit_text(
            f"⚠️ Êtes-vous sûr de vouloir supprimer *{product_name}* ?\n\n"
            "Cette action est irréversible !",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return SELECTING_PRODUCT_TO_DELETE
        
    except Exception as e:
        print(f"Erreur dans confirm_remove_product: {e}")
        return await show_admin_menu(update, context)

async def edit_product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le menu d'édition d'un produit"""
    query = update.callback_query
    await query.answer()
    
    try:
        _, product_id = query.data.split("_", 1)
        context.user_data['editing_product_id'] = product_id
        
        keyboard = [
            [InlineKeyboardButton("📝 Nom", callback_data="edit_name")],
            [InlineKeyboardButton("💰 Prix", callback_data="edit_price")],
            [InlineKeyboardButton("📝 Description", callback_data="edit_description")],
            [InlineKeyboardButton("🖼️ Photo/Vidéo", callback_data="edit_media")],
            [InlineKeyboardButton("🔙 Annuler", callback_data="cancel_edit")]
        ]
        
        await query.message.edit_text(
            "✏️ Que souhaitez-vous modifier ?\n"
            "Sélectionnez un champ à modifier:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDITING_PRODUCT
        
    except Exception as e:
        print(f"Erreur dans edit_product_menu: {e}")
        return await show_admin_menu(update, context)

async def daily_maintenance(context: ContextTypes.DEFAULT_TYPE):
    """Tâches de maintenance quotidiennes"""
    try:
        # Backup des données
        backup_data()
        
        # Nettoyage des utilisateurs inactifs
        await clean_inactive_users(context)
        
        # Nettoyage des stats
        clean_stats()
        
    except Exception as e:
        print(f"Erreur lors de la maintenance quotidienne : {e}")


    """Gère l'entrée de la description du produit"""
    description = update.message.text
    context.user_data['temp_product_description'] = description
    
    # Initialiser la liste des médias
    context.user_data['temp_product_media'] = []
    
    # Supprimer le message précédent
    await context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.message.message_id - 1
    )
    
    # Envoyer et sauvegarder l'ID du message d'invitation
    invitation_message = await update.message.reply_text(
        "📸 Envoyez les photos ou vidéos du produit (plusieurs possibles)\n"
        "Une fois terminé, cliquez sur Terminé :",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Terminé", callback_data="finish_media")],
            [InlineKeyboardButton("⏩ Ignorer", callback_data="skip_media")],
            [InlineKeyboardButton("🔙 Annuler", callback_data="cancel_add_product")]
        ])
    )
    context.user_data['media_invitation_message_id'] = invitation_message.message_id
    
    # Supprimer le message de l'utilisateur
    await update.message.delete()
    
    return WAITING_PRODUCT_MEDIA

async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre le processus d'ajout d'une catégorie"""
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="cancel_add_category")]]
    
    message_text = "📁 *Ajout d'une catégorie*\n\nEntrez le nom de la nouvelle catégorie :"
    
    await update.callback_query.answer()
    await update.callback_query.message.edit_text(
        text=message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return WAITING_CATEGORY_NAME

async def handle_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception du nom de la nouvelle catégorie"""
    category_name = update.message.text
    
    try:
        # Charger les catégories existantes
        with open('data/categories.json', 'r', encoding='utf-8') as f:
            categories = json.load(f)
    except FileNotFoundError:
        categories = []
    
    # Créer un nouvel ID unique
    new_id = str(max([int(cat['id']) for cat in categories] + [0]) + 1)
    
    # Ajouter la nouvelle catégorie
    categories.append({
        'id': new_id,
        'name': category_name
    })
    
    # Sauvegarder les modifications
    with open('data/categories.json', 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=4)
    
    # Confirmer l'ajout
    keyboard = [[InlineKeyboardButton("🔙 Retour au menu admin", callback_data="back_to_admin")]]
    await update.message.reply_text(
        f"✅ La catégorie *{category_name}* a été ajoutée avec succès !",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return CHOOSING

async def remove_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la liste des catégories à supprimer"""
    try:
        with open('data/categories.json', 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        keyboard = []
        for category in categories:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {category['name']}", 
                    callback_data=f"delete_category_{category['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="back_to_admin")])
        
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "🗑 *Suppression d'une catégorie*\n\nSélectionnez la catégorie à supprimer :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return REMOVING_CATEGORY
        
    except FileNotFoundError:
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_admin")]]
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "❌ Aucune catégorie n'existe actuellement.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING

async def handle_category_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la suppression d'une catégorie"""
    query = update.callback_query
    category_id = query.data.split('_')[2]
    
    try:
        # Charger les catégories
        with open('data/categories.json', 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        # Trouver et supprimer la catégorie
        category_name = ""
        categories = [cat for cat in categories if cat['id'] != category_id]
        
        # Sauvegarder les modifications
        with open('data/categories.json', 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=4)
        
        keyboard = [[InlineKeyboardButton("🔙 Retour au menu admin", callback_data="back_to_admin")]]
        await query.answer()
        await query.message.edit_text(
            f"✅ La catégorie a été supprimée avec succès !",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return CHOOSING
        
    except FileNotFoundError:
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_admin")]]
        await query.answer()
        await query.message.edit_text(
            "❌ Une erreur est survenue lors de la suppression de la catégorie.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING

async def handle_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception du nom du produit"""
    context.user_data['product_name'] = update.message.text
    
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="cancel_add_product")]]
    await update.message.reply_text(
        "📝 Entrez la description du produit :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return WAITING_PRODUCT_DESCRIPTION

async def handle_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception de la description du produit"""
    context.user_data['product_description'] = update.message.text
    
    keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="cancel_add_product")]]
    await update.message.reply_text(
        "💰 Entrez le prix du produit :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return WAITING_PRODUCT_PRICE

async def handle_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception du prix du produit"""
    try:
        price = float(update.message.text.replace(',', '.'))
        context.user_data['product_price'] = price
        
        keyboard = [
            [InlineKeyboardButton("✅ Terminer", callback_data="finish_media")],
            [InlineKeyboardButton("❌ Annuler", callback_data="cancel_add_product")]
        ]
        
        await update.message.reply_text(
            "🖼 Envoyez une ou plusieurs photos/vidéos du produit.\n"
            "Appuyez sur 'Terminer' une fois que vous avez fini.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        context.user_data['product_media'] = []
        return WAITING_PRODUCT_MEDIA
        
    except ValueError:
        keyboard = [[InlineKeyboardButton("❌ Annuler", callback_data="cancel_add_product")]]
        await update.message.reply_text(
            "❌ Prix invalide. Veuillez entrer un nombre valide :",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_PRODUCT_PRICE

async def handle_product_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception des médias du produit"""
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data['product_media'].append({'type': 'photo', 'file_id': file_id})
    elif update.message.video:
        file_id = update.message.video.file_id
        context.user_data['product_media'].append({'type': 'video', 'file_id': file_id})
    
    keyboard = [
        [InlineKeyboardButton("✅ Terminer", callback_data="finish_media")],
        [InlineKeyboardButton("❌ Annuler", callback_data="cancel_add_product")]
    ]
    
    await update.message.reply_text(
        f"✅ Média ajouté ! ({len(context.user_data['product_media'])} au total)\n"
        "Continuez à envoyer des médias ou appuyez sur 'Terminer'.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return WAITING_PRODUCT_MEDIA

async def finish_product_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Termine l'ajout des médias et passe à la sélection de la catégorie"""
    try:
        with open('data/categories.json', 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        keyboard = []
        for category in categories:
            keyboard.append([
                InlineKeyboardButton(
                    category['name'], 
                    callback_data=f"select_category_{category['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ Annuler", callback_data="cancel_add_product")])
        
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "📁 Sélectionnez une catégorie pour le produit :",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_PRODUCT_CATEGORY
        
    except FileNotFoundError:
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="back_to_admin")]]
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "❌ Erreur : Aucune catégorie n'existe. Veuillez d'abord créer une catégorie.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING

async def save_product(context: ContextTypes.DEFAULT_TYPE, category_id: str):
    """Sauvegarde le produit dans le fichier JSON"""
    try:
        with open('data/products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
    except FileNotFoundError:
        products = []
    
    # Créer un nouvel ID unique
    new_id = str(max([int(prod['id']) for prod in products] + [0]) + 1)
    
    # Créer le nouveau produit
    new_product = {
        'id': new_id,
        'name': context.user_data['product_name'],
        'description': context.user_data['product_description'],
        'price': context.user_data['product_price'],
        'media': context.user_data['product_media'],
        'category_id': category_id
    }
    
    # Ajouter le produit à la liste
    products.append(new_product)
    
    # Sauvegarder les modifications
    with open('data/products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)
    
    return new_product

async def handle_contact_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la modification du nom d'utilisateur de contact"""
    new_username = update.message.text.replace("@", "")
    CONFIG['contact_username'] = new_username
    
    # Sauvegarder la configuration
    with open('config/config.json', 'w', encoding='utf-8') as f:
        json.dump(CONFIG, f, indent=4)
    
    # Supprimer le message précédent
    await context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.message.message_id - 1
    )
    
    # Supprimer le message de l'utilisateur
    await update.message.delete()
    
    return await show_admin_menu(update, context)

async def handle_normal_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestion des boutons normaux"""
    query = update.callback_query
    await query.answer()

    if query.data == "admin":
        if str(update.effective_user.id) in ADMIN_IDS:
            return await show_admin_menu(update, context)
        else:
            await query.edit_message_text("❌ Vous n'êtes pas autorisé à accéder au menu d'administration.")
            return CHOOSING


    elif query.data == "add_category":
        await query.message.edit_text(
            "📝 Veuillez entrer le nom de la nouvelle catégorie:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Annuler", callback_data="cancel_add_category")
            ]])
        )
        return WAITING_CATEGORY_NAME

    elif query.data == "add_product":
        keyboard = []
        for category in CATALOG.keys():
            if category != 'stats':
                keyboard.append([InlineKeyboardButton(category, callback_data=f"select_category_{category}")])
        keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data="cancel_add_product")])
        
        await query.message.edit_text(
            "📝 Sélectionnez la catégorie pour le nouveau produit:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_CATEGORY

    elif query.data.startswith("select_category_"):
        # Ne traiter que si ce n'est PAS une action de suppression
        if not query.data.startswith("select_category_to_delete_"):
            category = query.data.replace("select_category_", "")
            context.user_data['temp_product_category'] = category
            
            await query.message.edit_text(
                "📝 Veuillez entrer le nom du nouveau produit:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Annuler", callback_data="cancel_add_product")
                ]])
            )
            return WAITING_PRODUCT_NAME

    elif query.data.startswith("delete_product_category_"):
        category = query.data.replace("delete_product_category_", "")
        products = CATALOG.get(category, [])
    
        keyboard = []
        for product in products:
            if isinstance(product, dict):
                keyboard.append([
                    InlineKeyboardButton(
                        product['name'], 
                        callback_data=f"confirm_delete_product_{category}_{product['name']}"
                    )
                ])
        keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data="cancel_delete_product")])
    
        await query.message.edit_text(
            f"⚠️ Sélectionnez le produit à supprimer de *{category}* :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return SELECTING_PRODUCT_TO_DELETE

    elif query.data == "delete_category":
        keyboard = []
        for category in CATALOG.keys():
            if category != 'stats':
                keyboard.append([InlineKeyboardButton(category, callback_data=f"confirm_delete_category_{category}")])
        keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data="cancel_delete_category")])
        
        await query.message.edit_text(
            "⚠️ Sélectionnez la catégorie à supprimer:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_CATEGORY_TO_DELETE

    elif query.data.startswith("confirm_delete_category_"):
        # Ajoutez une étape de confirmation
        category = query.data.replace("confirm_delete_category_", "")
        keyboard = [
            [
                InlineKeyboardButton("✅ Oui, supprimer", callback_data=f"really_delete_category_{category}"),
                InlineKeyboardButton("❌ Non, annuler", callback_data="cancel_delete_category")
            ]
        ]
        await query.message.edit_text(
            f"⚠️ *Êtes-vous sûr de vouloir supprimer la catégorie* `{category}` *?*\n\n"
            f"Cette action supprimera également tous les produits de cette catégorie.\n"
            f"Cette action est irréversible !",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return SELECTING_CATEGORY_TO_DELETE


    elif query.data.startswith("really_delete_category_"):
        category = query.data.replace("really_delete_category_", "")
        if category in CATALOG:
            del CATALOG[category]
            save_catalog(CATALOG)
            await query.message.edit_text(
                f"✅ La catégorie *{category}* a été supprimée avec succès !",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour au menu", callback_data="admin")
                ]])
            )
        return CHOOSING

    elif query.data == "delete_product":
        keyboard = []
        for category in CATALOG.keys():
            if category != 'stats':
                keyboard.append([
                    InlineKeyboardButton(
                        category, 
                        callback_data=f"delete_product_category_{category}"
                    )
                ])
        keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data="cancel_delete_product")])
        
        await query.message.edit_text(
            "⚠️ Sélectionnez la catégorie du produit à supprimer:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_CATEGORY_TO_DELETE

    elif query.data.startswith("confirm_delete_product_"):
        try:
            # Extraire la catégorie et le nom du produit
            parts = query.data.replace("confirm_delete_product_", "").split("_")
            category = parts[0]
            product_name = "_".join(parts[1:])  # Pour gérer les noms avec des underscores
        
            # Créer le clavier de confirmation
            keyboard = [
                [
                    InlineKeyboardButton("✅ Oui, supprimer", 
                        callback_data=f"really_delete_product_{category}_{product_name}"),
                    InlineKeyboardButton("❌ Non, annuler", 
                        callback_data="cancel_delete_product")
                ]
            ]
        
            await query.message.edit_text(
                f"⚠️ *Êtes-vous sûr de vouloir supprimer le produit* `{product_name}` *?*\n\n"
                f"Cette action est irréversible !",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return SELECTING_PRODUCT_TO_DELETE
        
        except Exception as e:
            print(f"Erreur lors de la confirmation de suppression: {e}")
            return await show_admin_menu(update, context)

    elif query.data.startswith("really_delete_product_"):
        try:
            parts = query.data.replace("really_delete_product_", "").split("_")
            category = parts[0]
            product_name = "_".join(parts[1:])
        
            if category in CATALOG:
                CATALOG[category] = [p for p in CATALOG[category] if p['name'] != product_name]
                save_catalog(CATALOG)
                await query.message.edit_text(
                    f"✅ Le produit *{product_name}* a été supprimé avec succès !",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour au menu", callback_data="admin")
                    ]])
                )
            return CHOOSING
        
        except Exception as e:
            print(f"Erreur lors de la suppression du produit: {e}")
            return await show_admin_menu(update, context)


    elif query.data == "show_stats":
        if 'stats' not in CATALOG:
            CATALOG['stats'] = {
                "total_views": 0,
                "category_views": {},
                "product_views": {},
                "last_updated": datetime.utcnow().strftime("%H:%M:%S"),  # Format heure uniquement
                "last_reset": datetime.utcnow().strftime("%Y-%m-%d")  # Format date uniquement
            }
        
        # Nettoyer les stats avant l'affichage
        clean_stats()
        
        stats = CATALOG['stats']
        text = "📊 *Statistiques du catalogue*\n\n"
        text += f"👥 Vues totales: {stats.get('total_views', 0)}\n"
        
        # Convertir le format de l'heure si nécessaire
        last_updated = stats.get('last_updated', 'Jamais')
        if len(last_updated) > 8:  # Si la date contient plus que HH:MM:SS
            try:
                last_updated = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            except:
                pass
        text += f"🕒 Dernière mise à jour: {last_updated}\n"
        
        if 'last_reset' in stats:
            text += f"🔄 Dernière réinitialisation: {stats.get('last_reset', 'Jamais')}\n"
        text += "\n"
        
        # Vues par catégorie
        text += "📈 *Vues par catégorie:*\n"
        category_views = stats.get('category_views', {})
        if category_views:
            sorted_categories = sorted(category_views.items(), key=lambda x: x[1], reverse=True)
            for category, views in sorted_categories:
                if category in CATALOG:  # Vérifier que la catégorie existe toujours
                    text += f"- {category}: {views} vues\n"
        else:
            text += "Aucune vue enregistrée.\n"

        # Séparateur
        text += "\n━━━━━━━━━━━━━━━\n\n"
        
        # Vues par produit
        text += "🔥 *Produits les plus populaires:*\n"
        product_views = stats.get('product_views', {})
        if product_views:
            # Créer une liste de tous les produits existants avec leurs vues
            all_products = []
            for category, products in product_views.items():
                if category in CATALOG:  # Vérifier que la catégorie existe
                    existing_products = [p['name'] for p in CATALOG[category]]
                    for product_name, views in products.items():
                        if product_name in existing_products:  # Vérifier que le produit existe
                            all_products.append((category, product_name, views))
            
            # Trier par nombre de vues et prendre les 5 premiers
            sorted_products = sorted(all_products, key=lambda x: x[2], reverse=True)[:5]
            for category, product_name, views in sorted_products:
                text += f"- {product_name} ({category}): {views} vues\n"
        else:
            text += "Aucune vue enregistrée sur les produits.\n"
        
        # Ajouter le bouton de réinitialisation des stats
        keyboard = [
            [InlineKeyboardButton("🔄 Réinitialiser les statistiques", callback_data="confirm_reset_stats")],
            [InlineKeyboardButton("🔙 Retour", callback_data="admin")]
        ]
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == "edit_contact":
        await query.message.edit_text(
            "📱 Veuillez entrer le nouveau nom d'utilisateur Telegram pour le contact (avec ou sans @):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Annuler", callback_data="cancel_edit_contact")
            ]])
        )
        return WAITING_CONTACT_USERNAME

    # Boutons d'annulation
    elif query.data in ["cancel_add_category", "cancel_add_product", "cancel_delete_category", 
                       "cancel_delete_product", "cancel_edit_contact"]:
        return await show_admin_menu(update, context)

    elif query.data == "back_to_categories":
        keyboard = []
        for category in CATALOG.keys():
            if category != 'stats':
                keyboard.append([InlineKeyboardButton(category, callback_data=f"view_{category}")])
        
        # Ajout des boutons de contact/redirection
        contact_buttons = [
        [
            InlineKeyboardButton("📞 Contact telegram", url=f"https://t.me/{CONFIG['contact_username']}"),
            InlineKeyboardButton("📝 Canal telegram", url="https://t.me/+LT2G6gMsMjY3MWFk"),
        ],
        [InlineKeyboardButton("🥔 Canal potato", url="https://doudlj.org/joinchat/5ZEmn25bOsTR7f-aYdvC0Q")]
    ]
        keyboard.extend(contact_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🌿 *Bienvenue chez Green Attack* 🌿\n\n"
            "Ceci n'est pas le produit final\n"
            "Ce bot est juste un bot test, pour tester mes conneries dessus.\n\n"
            "📱 Cliquez sur MENU pour voir les catégories\n"
        )
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif query.data == "skip_media":
        category = context.user_data.get('temp_product_category')
        if category:
            new_product = {
                'name': context.user_data.get('temp_product_name'),
                'price': context.user_data.get('temp_product_price'),
                'description': context.user_data.get('temp_product_description')
            }
            
            if category not in CATALOG:
                CATALOG[category] = []
            CATALOG[category].append(new_product)
            save_catalog(CATALOG)
            
            context.user_data.clear()
            return await show_admin_menu(update, context)

    elif query.data.startswith("product_"):
            _, category, product_name = query.data.split("_", 2)
            product = next((p for p in CATALOG[category] if p['name'] == product_name), None)
        
            if product:
                caption = f"📱 *{product['name']}*\n\n"
                caption += f"💰 *Prix:*\n{product['price']}\n\n"
                caption += f"📝 *Description:*\n{product['description']}"
            
                if 'media' in product and product['media']:
                    media_list = product['media']
                    media_list = sorted(media_list, key=lambda x: x.get('order_index', 0))
                    total_media = len(media_list)
                    context.user_data['current_media_index'] = 0  # AJOUTER CETTE LIGNE
                    current_media = media_list[0]
                
                    keyboard = []
                    if total_media > 1:
                        keyboard.append([
                            InlineKeyboardButton("⬅️ Précédent", callback_data=f"prev_media_{category}_{product_name}"),
                            InlineKeyboardButton("➡️ Suivant", callback_data=f"next_media_{category}_{product_name}")
                        ])
                    keyboard.append([InlineKeyboardButton("🔙 Retour à la catégorie", callback_data=f"view_{category}")])
                
                    await query.message.delete()
                
                    if current_media['media_type'] == 'photo':
                        message = await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=current_media['media_id'],
                            caption=caption,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                        context.user_data['last_product_message_id'] = message.message_id
                    else:
                        message = await context.bot.send_video(
                            chat_id=query.message.chat_id,
                            video=current_media['media_id'],
                            caption=caption,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
            if product:
                # Incrémenter les stats du produit
                if 'stats' not in CATALOG:
                    CATALOG['stats'] = {...}  # même initialisation que ci-dessus
    
                if 'product_views' not in CATALOG['stats']:
                    CATALOG['stats']['product_views'] = {}
                if category not in CATALOG['stats']['product_views']:
                    CATALOG['stats']['product_views'][category] = {}
                if product['name'] not in CATALOG['stats']['product_views'][category]:
                    CATALOG['stats']['product_views'][category][product['name']] = 0
    
                CATALOG['stats']['product_views'][category][product['name']] += 1
                CATALOG['stats']['total_views'] += 1
                CATALOG['stats']['last_updated'] = datetime.utcnow().strftime("%H:%M:%S")
                save_catalog(CATALOG)

    # Ajoutez ces gestionnaires pour la navigation entre les médias
    elif query.data.startswith(("next_media_", "prev_media_")):
            try:
                _, direction, category, product_name = query.data.split("_", 3)
                product = next((p for p in CATALOG[category] if p['name'] == product_name), None)

                if product and 'media' in product:
                    media_list = sorted(product['media'], key=lambda x: x.get('order_index', 0))
                    total_media = len(media_list)
                    current_index = context.user_data.get('current_media_index', 0)

                    # Navigation simple
                    if direction == "next":
                        current_index = current_index + 1
                        if current_index >= total_media:
                            current_index = 0
                    else:  # prev
                        current_index = current_index - 1
                        if current_index < 0:
                            current_index = total_media - 1

                    # Une seule fois !
                    context.user_data['current_media_index'] = current_index
                    current_media = media_list[current_index]

                    caption = f"📱 *{product['name']}*\n\n"
                    caption += f"💰 *Prix:*\n{product['price']}\n\n"
                    caption += f"📝 *Description:*\n{product['description']}"

                    keyboard = []
                    if total_media > 1:
                        keyboard.append([
                            InlineKeyboardButton("⬅️ Précédent", callback_data=f"prev_media_{category}_{product_name}"),
                            InlineKeyboardButton("➡️ Suivant", callback_data=f"next_media_{category}_{product_name}")
                        ])
                    keyboard.append([InlineKeyboardButton("🔙 Retour à la catégorie", callback_data=f"view_{category}")])

                    try:
                        await query.message.delete()
                    except Exception as e:
                        print(f"Erreur lors de la suppression du message: {e}")

                    if current_media['media_type'] == 'photo':
                        message = await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=current_media['media_id'],
                            caption=caption,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                    else:  # video
                        message = await context.bot.send_video(
                            chat_id=query.message.chat_id,
                            video=current_media['media_id'],
                            caption=caption,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                    context.user_data['last_product_message_id'] = message.message_id

            except Exception as e:
                print(f"Erreur lors de la navigation des médias: {e}")
                await query.answer("Une erreur est survenue")

    elif query.data == "show_categories":
        keyboard = []
        # Créer uniquement les boutons de catégories
        for category in CATALOG.keys():
            if category != 'stats':
                keyboard.append([InlineKeyboardButton(category, callback_data=f"view_{category}")])
    
        # Ajouter uniquement le bouton retour à l'accueil
        keyboard.append([InlineKeyboardButton("🔙 Retour à l'accueil", callback_data="back_to_home")])
    
        new_text = "📋 *Menu des catégories*\n\n" \
                   "Choisissez une catégorie pour voir les produits :"
    
        # Vérifier si le message est différent avant de le modifier
        if query.message.text != new_text or query.message.reply_markup != InlineKeyboardMarkup(keyboard):
            await query.edit_message_text(
                new_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await query.answer()

    elif query.data == "edit_product":
        keyboard = []
        for category in CATALOG.keys():
            if category != 'stats':
                keyboard.append([
                    InlineKeyboardButton(
                        category, 
                        callback_data=f"editcat_{category}"  # Raccourci ici
                    )
                ])
        keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data="cancel_edit")])
        
        await query.message.edit_text(
            "✏️ Sélectionnez la catégorie du produit à modifier:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_CATEGORY

    elif query.data.startswith("editcat_"):  # Nouveau gestionnaire avec nom plus court
        category = query.data.replace("editcat_", "")
        products = CATALOG.get(category, [])
        
        keyboard = []
        for product in products:
            if isinstance(product, dict):
                # Créer un callback_data plus court
                callback_data = f"editp_{category}_{product['name']}"[:64]  # Limite à 64 caractères
                keyboard.append([
                    InlineKeyboardButton(product['name'], callback_data=callback_data)
                ])
        keyboard.append([InlineKeyboardButton("🔙 Annuler", callback_data="cancel_edit")])
        
        await query.message.edit_text(
            f"✏️ Sélectionnez le produit à modifier dans {category}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_PRODUCT_TO_EDIT

    elif query.data.startswith("editp_"):
        try:
            _, category, product_name = query.data.split("_", 2)
            context.user_data['editing_category'] = category
            context.user_data['editing_product'] = product_name
            
            keyboard = [
                [InlineKeyboardButton("📝 Nom", callback_data="edit_name")],
                [InlineKeyboardButton("💰 Prix", callback_data="edit_price")],
                [InlineKeyboardButton("📝 Description", callback_data="edit_desc")],
                [InlineKeyboardButton("🖼️ Photo/Vidéo", callback_data="edit_media")],
                [InlineKeyboardButton("🔙 Annuler", callback_data="cancel_edit")]
            ]
            
            await query.message.edit_text(
                f"✏️ Que souhaitez-vous modifier pour *{product_name}* ?\n"
                "Sélectionnez un champ à modifier:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return EDITING_PRODUCT_FIELD
        except Exception as e:
            print(f"Erreur dans editp_: {e}")
            return await show_admin_menu(update, context)

    elif query.data in ["edit_name", "edit_price", "edit_desc", "edit_media"]:
        field_mapping = {
            "edit_name": "name",
            "edit_price": "price",
            "edit_desc": "description",
            "edit_media": "media"
        }
        field = field_mapping[query.data]
        context.user_data['editing_field'] = field
        
        category = context.user_data.get('editing_category')
        product_name = context.user_data.get('editing_product')
        
        product = next((p for p in CATALOG[category] if p['name'] == product_name), None)
        
        if product:
            current_value = product.get(field, "Non défini")
            if field == 'media':
                await query.message.edit_text(
                    "📸 Envoyez une nouvelle photo ou vidéo pour ce produit:\n"
                    "(ou cliquez sur Annuler pour revenir en arrière)",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Annuler", callback_data="cancel_edit")
                    ]])
                )
                return WAITING_PRODUCT_MEDIA
            else:
                field_names = {
                    'name': 'nom',
                    'price': 'prix',
                    'description': 'description'
                }
                await query.message.edit_text(
                    f"✏️ Modification du {field_names.get(field, field)}\n"
                    f"Valeur actuelle : {current_value}\n\n"
                    "Envoyez la nouvelle valeur :",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Annuler", callback_data="cancel_edit")
                    ]])
                )
                return WAITING_NEW_VALUE

    elif query.data == "cancel_edit":
        return await show_admin_menu(update, context)

    elif query.data == "confirm_reset_stats":
        # Demander confirmation avant de réinitialiser
        keyboard = [
            [
                InlineKeyboardButton("✅ Oui, réinitialiser", callback_data="reset_stats_confirmed"),
                InlineKeyboardButton("❌ Non, annuler", callback_data="admin")
            ]
        ]
        
        await query.message.edit_text(
            "⚠️ *Êtes-vous sûr de vouloir réinitialiser toutes les statistiques ?*\n\n"
            "Cette action est irréversible et supprimera :\n"
            "• Toutes les vues des catégories\n"
            "• Toutes les vues des produits\n"
            "• Le compteur de vues total",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    elif query.data == "reset_stats_confirmed":
        # Réinitialiser les statistiques
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        CATALOG['stats'] = {
            "total_views": 0,
            "category_views": {},
            "product_views": {},
            "last_updated": now.strftime("%H:%M:%S"),         # Juste l'heure
            "last_reset": now.strftime("%Y-%m-%d")           # Juste la date
        }
        save_catalog(CATALOG)
        
        # Afficher un message de confirmation
        keyboard = [[InlineKeyboardButton("🔙 Retour au menu", callback_data="admin")]]
        await query.message.edit_text(
            "✅ *Les statistiques ont été réinitialisées avec succès!*\n\n"
            f"Date de réinitialisation : {CATALOG['stats']['last_reset']}\n\n"
            "Toutes les statistiques sont maintenant à zéro.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data.startswith("view_"):
            category = query.data.replace("view_", "")
            if category in CATALOG:
                # D'abord supprimer le message de produit actuel
                try:
                    await query.message.delete()
                except Exception as e:
                    print(f"Erreur lors de la suppression du message de query: {e}")

                # Si on a un message produit précédent, le supprimer aussi
                if 'last_product_message_id' in context.user_data:
                    try:
                        await context.bot.delete_message(
                            chat_id=query.message.chat_id,
                            message_id=context.user_data['last_product_message_id']
                        )
                        del context.user_data['last_product_message_id']
                    except Exception as e:
                        print(f"Erreur lors de la suppression du message produit: {e}")

            if category in CATALOG:
                # Incrémenter le compteur total
                if 'stats' not in CATALOG:
                    CATALOG['stats'] = {
                        "total_views": 0,
                        "category_views": {},
                        "product_views": {},
                        "last_updated": datetime.utcnow().strftime("%H:%M:%S")
                    }
    
                # Incrémenter les vues de la catégorie
                if 'category_views' not in CATALOG['stats']:
                    CATALOG['stats']['category_views'] = {}
                if category not in CATALOG['stats']['category_views']:
                    CATALOG['stats']['category_views'][category] = 0
                CATALOG['stats']['category_views'][category] += 1
    
                CATALOG['stats']['total_views'] += 1
                CATALOG['stats']['last_updated'] = datetime.utcnow().strftime("%H:%M:%S")
                save_catalog(CATALOG)

                products = CATALOG[category]
                # Afficher la liste des produits
                text = f"*{category}*\n\n"
                keyboard = []
                for product in products:
                    keyboard.append([InlineKeyboardButton(
                        product['name'],
                        callback_data=f"product_{category}_{product['name']}"
                    )])
            
                keyboard.append([InlineKeyboardButton("🔙 Retour au menu", callback_data="show_categories")])
            
                # Envoyer un nouveau message avec la liste des produits
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )    
                
    elif query.data == "show_categories":
        keyboard = []
        # Créer uniquement les boutons de catégories
        for category in CATALOG.keys():
            if category != 'stats':
                keyboard.append([InlineKeyboardButton(category, callback_data=f"view_{category}")])
        
        # Ajouter uniquement le bouton retour à l'accueil
        keyboard.append([InlineKeyboardButton("🔙 Retour à l'accueil", callback_data="back_to_home")])
        
        await query.edit_message_text(
            "📋 *Menu des catégories*\n\n"
            "Choisissez une catégorie pour voir les produits :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == "back_to_home":
        # Créer le keyboard de base
        keyboard = [
            [InlineKeyboardButton("📋 MENU", callback_data="show_categories")]
        ]
    

        if str(update.effective_user.id) in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("🔧 Menu Admin", callback_data="admin")])
    

        keyboard.extend([
            [
                InlineKeyboardButton("📞 Contact telegram", url=f"https://t.me/{CONFIG['contact_username']}"),
                InlineKeyboardButton("📝 Canal telegram", url="https://t.me/+LT2G6gMsMjY3MWFk"),
            ],
            [InlineKeyboardButton("🥔 Canal potato", url="https://doudlj.org/joinchat/5ZEmn25bOsTR7f-aYdvC0Q")]
        ])
        
        welcome_text = (
            "🌿 *Bienvenue sur le bot test de DDLAD* 🌿\n\n"
            "Ceci n'est pas le produit final'.\n"
            "Ce bot est juste un bot test, pour tester mes conneries dessus.\n\n"
            "📋 Cliquez sur MENU pour voir les catégories"
        )
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data == "start_broadcast":
        if str(update.effective_user.id) not in ADMIN_IDS:
            await query.answer("❌ Vous n'êtes pas autorisé à utiliser cette fonction.")
            return CHOOSING
            
        await query.message.edit_text(
            "📢 *Mode Diffusion*\n\n"
            "Envoyez le message que vous souhaitez diffuser à tous les utilisateurs.\n"
            "Le message peut contenir du texte, des photos ou des vidéos.\n\n"
            "Pour annuler, cliquez sur Annuler.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Annuler", callback_data="cancel_broadcast")
            ]])
        )
        return WAITING_BROADCAST_MESSAGE

    elif query.data == "cancel_broadcast":
        return await show_admin_menu(update, context)

    elif query.data == "manage_users":
            active_users = context.bot_data.get('active_users', {})
            if 'active_users' not in context.bot_data:
                context.bot_data['active_users'] = load_active_users()
        
            cleaned = await clean_inactive_users(context)
        
            # Créer le texte sans formatage spécial d'abord
            text = "👥 Gestion des utilisateurs\n\n"
            text += f"Utilisateurs actifs : {len(active_users)}\n"
            text += f"Utilisateurs nettoyés : {cleaned}\n\n"
            text += "Liste des utilisateurs actifs :\n"
        
            # Liste des utilisateurs (limité à 20)
            for user_id, user_data in list(active_users.items())[:20]:
                username = user_data.get('username', '')
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                last_seen = user_data.get('last_seen', 'Inconnu')
            
                full_name = f"{first_name} {last_name}".strip() or "Nom inconnu"
            
                text += f"\n• {full_name}"
                if username:
                    text += f" (@{username})"
                text += f"\nDernière activité : {last_seen}\n"
        
            if len(active_users) > 20:
                text += f"\n... et {len(active_users) - 20} autres utilisateurs"
        
            keyboard = [
                [InlineKeyboardButton("🔄 Nettoyer la liste", callback_data="clean_users")],
                [InlineKeyboardButton("🔙 Retour", callback_data="admin")]
            ]
        
            # Envoyer le message sans parse_mode
            await query.message.edit_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "clean_users":
            try:
                # Afficher un message de chargement
                await query.answer("🔄 Vérification des utilisateurs...")
                initial_count = len(context.bot_data.get('active_users', {}))
                cleaned = await clean_inactive_users(context)
                final_count = len(context.bot_data.get('active_users', {}))
            
                text = "👥 Rapport de vérification\n\n"
                text += f"• Utilisateurs scannés : {initial_count}\n"
            
                if cleaned > 0:
                    text += f"• Utilisateurs supprimés : {cleaned}\n"
                    text += f"• Utilisateurs restants : {final_count}\n"
                else:
                    text += "✅ Tous les utilisateurs sont actifs !\n"
            
                text += "\nListe des utilisateurs :\n"
            
                # Liste des utilisateurs actifs
                active_users = context.bot_data.get('active_users', {})
                for user_id, user_data in list(active_users.items())[:20]:
                    username = user_data.get('username', '')
                    first_name = user_data.get('first_name', '')
                    last_name = user_data.get('last_name', '')
                    last_seen = user_data.get('last_seen', 'Inconnu')
                
                    full_name = f"{first_name} {last_name}".strip() or "Nom inconnu"
                    text += f"\n• {full_name}"
                    if username:
                        text += f" (@{username})"
                    text += f"\nDernière activité : {last_seen}\n"
            
                if len(active_users) > 20:
                    text += f"\n... et {len(active_users) - 20} autres utilisateurs"
            
                keyboard = [
                    [InlineKeyboardButton("🔄 Vérifier à nouveau", callback_data="clean_users")],
                    [InlineKeyboardButton("🔙 Retour", callback_data="admin")]
                ]
            
                await query.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
            except Exception as e:
                print(f"[ERROR] Erreur lors du nettoyage : {e}")
                # Message de fallback en cas d'erreur
                await query.message.edit_text(
                    "Une erreur est survenue lors du nettoyage.\n"
                    "Veuillez réessayer plus tard.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour", callback_data="admin")
                    ]])
                )

async def handle_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la nouvelle valeur pour le champ en cours de modification"""
    category = context.user_data.get('editing_category')
    product_name = context.user_data.get('editing_product')
    field = context.user_data.get('editing_field')
    new_value = update.message.text
    
    if not all([category, product_name, field]):
        await update.message.reply_text("❌ Une erreur est survenue. Veuillez réessayer.")
        return await show_admin_menu(update, context)
    
    # Trouver et modifier le produit
    for product in CATALOG.get(category, []):
        if product['name'] == product_name:
            old_value = product.get(field)
            product[field] = new_value
            save_catalog(CATALOG)
            
            # Supprimer les messages précédents
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id - 1
            )
            await update.message.delete()
            
            # Envoyer confirmation
            keyboard = [[InlineKeyboardButton("🔙 Retour au menu", callback_data="admin")]]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Modification effectuée avec succès !\n\n"
                     f"Ancien {field}: {old_value}\n"
                     f"Nouveau {field}: {new_value}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            break
    
    return CHOOSING

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler temporaire pour obtenir le file_id de l'image banner"""
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        CONFIG['banner_image'] = file_id
        # Sauvegarder dans config.json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, indent=4)
        await update.message.reply_text(
            f"✅ Image banner enregistrée!\nFile ID: {file_id}"
        )

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'envoi du message de broadcast"""
    if str(update.effective_user.id) not in ADMIN_IDS:
        await update.message.reply_text("❌ Vous n'êtes pas autorisé à utiliser cette fonction.")
        return CHOOSING

    try:
        if 'active_users' not in context.bot_data:
            context.bot_data['active_users'] = load_active_users()
        
        active_users = context.bot_data['active_users']
        
        # Convertir en dictionnaire si c'est encore un set
        if isinstance(active_users, set):
            active_users = {user_id: {
                'username': None,
                'first_name': None,
                'last_name': None,
                'last_seen': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            } for user_id in active_users}
            context.bot_data['active_users'] = active_users
        
        if not active_users:
            await update.message.reply_text(
                "❌ Aucun utilisateur actif trouvé.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour au menu admin", callback_data="admin")
                ]])
            )
            return CHOOSING

        success_count = 0
        fail_count = 0
        users_to_remove = set()  # Utiliser un set pour stocker les IDs à supprimer
        
        # Envoyer le message à chaque utilisateur
        for user_id in list(active_users.keys()):
            try:
                if update.message.photo:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=update.message.photo[-1].file_id,
                        caption=update.message.caption if update.message.caption else None,
                        parse_mode='Markdown'
                    )
                elif update.message.video:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=update.message.video.file_id,
                        caption=update.message.caption if update.message.caption else None,
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=update.message.text,
                        parse_mode='Markdown'
                    )
                success_count += 1
                # Mettre à jour la dernière activité
                active_users[user_id]['last_seen'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"Erreur d'envoi à {user_id}: {e}")
                fail_count += 1
                if "bot was blocked" in str(e).lower() or "chat not found" in str(e).lower():
                    users_to_remove.add(user_id)

        # Supprimer les utilisateurs inactifs
        for user_id in users_to_remove:
            del active_users[user_id]
        
        # Sauvegarder les changements
        save_active_users(active_users)

        # Envoyer le rapport
        report = (
            "📊 *Rapport de diffusion*\n\n"
            f"✅ Envois réussis : {success_count}\n"
            f"❌ Échecs : {fail_count}\n"
            f"📨 Total : {success_count + fail_count}\n\n"
            f"👥 Utilisateurs actifs restants : {len(active_users)}"
        )
        
        await update.message.reply_text(
            report,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour au menu admin", callback_data="admin")
            ]])
        )
        
    except Exception as e:
        print(f"Erreur lors du broadcast: {e}")
        await update.message.reply_text(
            f"❌ Une erreur est survenue : {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour au menu admin", callback_data="admin")
            ]])
        )
    
    return CHOOSING

async def clean_inactive_users(context: ContextTypes.DEFAULT_TYPE):
    """Nettoie la liste des utilisateurs inactifs"""
    if 'active_users' not in context.bot_data:
        context.bot_data['active_users'] = load_active_users()
    
    active_users = context.bot_data['active_users'].copy()  # Créer une copie pour éviter les modifications pendant l'itération
    inactive_users = set()
    
    print(f"[DEBUG] Début du nettoyage - {datetime.utcnow()}")
    print(f"[DEBUG] Utilisateurs actuels: {len(active_users)}")
    
    for user_id in list(active_users.keys()):
        try:
            print(f"[DEBUG] Vérification de l'utilisateur {user_id}")
            
            # Première tentative : send_chat_action
            try:
                await context.bot.send_chat_action(chat_id=user_id, action="typing")
                await asyncio.sleep(0.1)  # Petit délai
            except Exception as e:
                print(f"[DEBUG] Échec send_chat_action pour {user_id}: {str(e)}")
                if "blocked" in str(e).lower() or "not found" in str(e).lower() or "deactivated" in str(e).lower():
                    raise  # Forcer le passage au except externe
                
            # Deuxième tentative : get_chat
            try:
                chat = await context.bot.get_chat(user_id)
                active_users[user_id] = {
                    'username': chat.username,
                    'first_name': chat.first_name,
                    'last_name': chat.last_name,
                    'last_seen': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                }
                print(f"[DEBUG] Utilisateur {user_id} actif et mis à jour")
            except Exception as e:
                print(f"[DEBUG] Échec get_chat pour {user_id}: {str(e)}")
                raise  # Forcer le passage au except externe
                
        except Exception as e:
            print(f"[DEBUG] Utilisateur {user_id} marqué comme inactif: {str(e)}")
            inactive_users.add(user_id)
            print(f"[DEBUG] Utilisateur {user_id} marqué comme inactif")
            print(f"[DEBUG] Raison : {str(e)}")
        
        await asyncio.sleep(0.2)  # Délai entre chaque utilisateur
    
    # Supprimer les utilisateurs inactifs
    users_removed = 0
    for user_id in inactive_users:
        if user_id in active_users:
            print(f"[DEBUG] Suppression de l'utilisateur {user_id}")
            del active_users[user_id]
            users_removed += 1
    
    # Mettre à jour context.bot_data
    context.bot_data['active_users'] = active_users
    save_active_users(active_users)
    
    print(f"[DEBUG] Fin du nettoyage - Utilisateurs restants: {len(active_users)}")
    print(f"[DEBUG] Utilisateurs supprimés: {users_removed}")
    
    return users_removed

def main():
    """Fonction principale du bot"""
    try:
        # Créer l'application
        application = Application.builder().token(TOKEN).build()

        # Gestionnaire de conversation principal
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                CHOOSING: [
                    # Gestion des catégories et du catalogue
                    CallbackQueryHandler(ui_handler.show_categories, pattern='^show_categories$'),
                    CallbackQueryHandler(ui_handler.show_products, pattern='^category_'),
                    CallbackQueryHandler(ui_handler.show_product_details, pattern='^product_'),
            
                    # Gestion du menu admin et ses fonctionnalités
                    CallbackQueryHandler(admin, pattern='^admin$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^add_product$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^edit_product$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^remove_product$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^broadcast$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^manage_access$'),
                    CallbackQueryHandler(add_category, pattern='^add_category$'),
                    CallbackQueryHandler(remove_category, pattern='^remove_category$'),
            
                    # Gestion des autres boutons du menu principal
                    CallbackQueryHandler(about, pattern='^about$'),
                    CallbackQueryHandler(contact, pattern='^contact$'),
                    CallbackQueryHandler(ui_handler.show_home, pattern='^back_to_home$')
                ],
        
                SELECTING_CATEGORY: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^select_category_'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_'),
                    CallbackQueryHandler(admin, pattern='^back_to_admin$')
                ],

                WAITING_PRODUCT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_name),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_PRODUCT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_description),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_PRODUCT_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_price),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_PRODUCT_MEDIA: [
                    MessageHandler(filters.PHOTO | filters.VIDEO, handle_product_media),
                    CallbackQueryHandler(finish_product_media, pattern='^finish_media$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_PRODUCT_CATEGORY: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^select_category_'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                CONFIRM_ADD_PRODUCT: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^confirm_add_product$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                CHOOSING_PRODUCT_TO_REMOVE: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^remove_product_'),
                    CallbackQueryHandler(admin, pattern='^back_to_admin$')
                ],

                CHOOSING_PRODUCT_TO_EDIT: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^edit_product_'),
                    CallbackQueryHandler(admin, pattern='^back_to_admin$')
                ],

                WAITING_CATEGORY_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_name),
                    CallbackQueryHandler(admin, pattern='^cancel_add_category$')
                ],
        
                REMOVING_CATEGORY: [
                    CallbackQueryHandler(handle_category_deletion, pattern='^delete_category_'),
                    CallbackQueryHandler(admin, pattern='^back_to_admin$')
                ],

                EDITING_PRODUCT: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^edit_name$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^edit_description$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^edit_price$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^edit_media$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^edit_category$'),
                    CallbackQueryHandler(admin, pattern='^back_to_admin$')
                ],

                WAITING_NEW_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_value),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_NEW_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_value),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_NEW_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_value),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_NEW_MEDIA: [
                    MessageHandler(filters.PHOTO | filters.VIDEO, handle_product_media),
                    CallbackQueryHandler(finish_product_media, pattern='^finish_media$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_NEW_CATEGORY: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^select_category_'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_')
                ],

                WAITING_PRODUCT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_name),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_add_product$')
                ],
        
                WAITING_PRODUCT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_description),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_add_product$')
                ],
        
                WAITING_PRODUCT_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_price),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_add_product$')
                ],
        
                WAITING_PRODUCT_MEDIA: [
                    MessageHandler(filters.PHOTO | filters.VIDEO, handle_product_media),
                    CallbackQueryHandler(finish_product_media, pattern='^finish_media$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_add_product$')
                ],
        
                WAITING_PRODUCT_CATEGORY: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^select_category_'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^cancel_add_product$')
                ],

                WAITING_ACCESS_CODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, access_control.verify_code),
                    CallbackQueryHandler(ui_handler.show_home, pattern='^back_to_home$')
                ],

                MANAGE_ACCESS: [
                    CallbackQueryHandler(handle_normal_buttons, pattern='^generate_code$'),
                    CallbackQueryHandler(handle_normal_buttons, pattern='^revoke_access$'),
                    CallbackQueryHandler(admin, pattern='^back_to_admin$')
                ],
            },
            fallbacks=[
                CommandHandler('start', start),
                CommandHandler('cancel', cancel)
            ],
            name="main_conversation",
            persistent=False
        )
    
        application.add_handler(conv_handler)
        application.job_queue.run_daily(daily_maintenance, time=time(hour=0, minute=0))
        application.add_handler(CallbackQueryHandler(access_control.toggle_access_control, 
                                                pattern="^toggle_access_control$"))
        application.add_handler(CallbackQueryHandler(access_control.generate_new_code, 
                                                pattern="^generate_code$"))
        # Démarrer le bot
        print("Bot démarré...")
        application.run_polling()

    except Exception as e:
        print(f"Erreur lors du démarrage du bot: {e}")

if __name__ == '__main__':
    main()