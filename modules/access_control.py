import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# États pour le ConversationHandler
WAITING_ACCESS_CODE = 'WAITING_ACCESS_CODE'

class AccessControl:
    def __init__(self, config, save_config_callback, admin_ids):
        self.CONFIG = config
        self.save_config = save_config_callback
        self.ADMIN_IDS = admin_ids
        
        # Initialiser la configuration si elle n'existe pas
        if 'access_control' not in self.CONFIG:
            self.CONFIG['access_control'] = {
                'enabled': False,
                'valid_codes': {}
            }
            self.save_config()

    def generate_code(self) -> str:
        """Génère un code d'accès unique de 8 caractères"""
        characters = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(characters, k=8))
        
        self.CONFIG['access_control']['valid_codes'][code] = {
            'used': False,
            'created_at': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_config()
        return code

    def validate_code(self, code: str) -> bool:
        """Vérifie si un code est valide et non utilisé"""
        if not self.CONFIG['access_control']['enabled']:
            return True
            
        if code not in self.CONFIG['access_control']['valid_codes']:
            return False
            
        code_info = self.CONFIG['access_control']['valid_codes'][code]
        if code_info['used']:
            return False
            
        # Marquer le code comme utilisé
        self.CONFIG['access_control']['valid_codes'][code]['used'] = True
        self.save_config()
        return True

    def clean_old_codes(self):
        """Nettoie les codes plus vieux que 24h"""
        current_time = datetime.utcnow()
        codes_to_remove = []
        
        for code, info in self.CONFIG['access_control']['valid_codes'].items():
            created_at = datetime.strptime(info['created_at'], "%Y-%m-%d %H:%M:%S")
            if current_time - created_at > timedelta(hours=24):
                codes_to_remove.append(code)
                
        for code in codes_to_remove:
            del self.CONFIG['access_control']['valid_codes'][code]
        
        self.save_config()

    def get_active_codes_count(self) -> int:
        """Retourne le nombre de codes actifs non utilisés"""
        return len([c for c in self.CONFIG['access_control']['valid_codes'].values() 
                   if not c['used']])

    async def handle_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ajoute les options de contrôle d'accès au menu admin"""
        keyboard = [
            [InlineKeyboardButton(
                "🔒 Désactiver contrôle d'accès" if self.CONFIG['access_control']['enabled'] 
                else "🔓 Activer contrôle d'accès", 
                callback_data="toggle_access_control"
            )],
            [InlineKeyboardButton("🎫 Générer code d'accès", callback_data="generate_code")]
        ]
        return keyboard

    async def toggle_access_control(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Active/désactive le contrôle d'accès"""
        query = update.callback_query
        if str(query.from_user.id) not in self.ADMIN_IDS:
            await query.answer("Non autorisé")
            return False

        self.CONFIG['access_control']['enabled'] = not self.CONFIG['access_control']['enabled']
        self.save_config()
        
        await query.answer(
            "Contrôle d'accès " + 
            ("activé" if self.CONFIG['access_control']['enabled'] else "désactivé")
        )
        return True

    async def generate_new_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Génère un nouveau code d'accès"""
        query = update.callback_query
        if str(query.from_user.id) not in self.ADMIN_IDS:
            await query.answer("Non autorisé")
            return

        self.clean_old_codes()
        new_code = self.generate_code()
        
        await query.message.reply_text(
            f"🎫 Nouveau code généré :\n`{new_code}`\n\n"
            "Ce code est à usage unique et valable 24h.",
            parse_mode='Markdown'
        )

    async def check_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vérifie si l'utilisateur a accès"""
        user_id = str(update.effective_user.id)
        
        # Les admins ont toujours accès
        if user_id in self.ADMIN_IDS:
            return True
            
        # Si le contrôle d'accès est désactivé, accès direct
        if not self.CONFIG['access_control']['enabled']:
            return True
            
        # Vérifier si l'accès a déjà été accordé
        if context.user_data.get('access_granted'):
            return True
            
        # Demander le code d'accès
        await update.message.reply_text(
            "🔒 Ce bot nécessite un code d'accès.\n"
            "Veuillez entrer votre code :"
        )
        return False

    async def verify_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vérifie le code d'accès entré par l'utilisateur"""
        code = update.message.text.strip().upper()
        
        if self.validate_code(code):
            context.user_data['access_granted'] = True
            return True
        else:
            await update.message.reply_text(
                "❌ Code invalide ou déjà utilisé.\n"
                "Veuillez réessayer ou contacter un administrateur."
            )
            return False