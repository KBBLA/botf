#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot Telegram - Vente de bases de données
- Interface identique à la version précédente
- Paiements en BTC/ETH/SOL avec vérification automatique
- Taux de change en direct via CoinGecko
- Vérification via Blockstream, Etherscan, Solscan
- Pas de clic "J'ai payé" - tout est automatique
"""
import os
import sys
import time
import logging
import json
import glob
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

# ========== CAPTURE D'ERREUR AU DÉMARRAGE ==========
try:
    print("=== DÉMARRAGE BOT ===", flush=True)
    print("Import des modules OK", flush=True)
except Exception as e:
    print("ERREUR AU DÉMARRAGE:", str(e), flush=True)
    sys.exit(1)

# ========== AJOUTE CES LIGNES ICI ==========
# Pour Render Web Service
import threading
import sys

port = int(os.environ.get('PORT', 10000))
print(f"Bot démarré sur le port {port}", flush=True)

def keep_alive():
    while True:
        print("Bot actif...", file=sys.stdout, flush=True)
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()
# ============================================
# ========== AJOUTE CES LIGNES ICI ==========
# Pour Render Web Service
import threading
import time
import sys

port = int(os.environ.get('PORT', 10000))
print(f"Bot démarré sur le port {port}")

def keep_alive():
    while True: 
     print("Bot actif...", file=sys.stdout)
     time.sleep(300)

# Lance la fonction keep_alive en arrière-plan
threading.Thread(target=keep_alive, daemon=True).start()
# ============================================

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8695192616:AAEkXEBS3Hlw8G5ZhPBOGJpfHdvTKvnAEJ0"

# Tes adresses de réception
TA_ADRESSE_BTC = "bc1qyawv8j0mpxywqct8tntt96mqv8wnww4fxu0yg0"
TA_ADRESSE_ETH = "0xF8b46473e778406d1F9911932eaa423E028fA492"
TA_ADRESSE_SOL = "CJGz8F4SHzvVhZPr9k22v3rwgzMndQ5J5ssucND29B4V"

# Clé API Etherscan (gratuite)
ETHERSCAN_API_KEY = "27Z4U12FJN5J4NPVTJSJJ1ZS1CY7F44NRV"

# Admins (à modifier avec tes IDs)
ADMINS = [
    {"id": 8295467733, "pourcentage": 100, "nom": "Admin"}  # Remplace par ton ID
]
ADMIN_IDS = [admin["id"] for admin in ADMINS]

WELCOME_MSG = "🛍️ *Bienvenue chez BLACKCAT !*"
DOSSIER_BASES = "bases"
DATA_DIR = "data"
PRIX_PAR_MILLE = 50  # en euros
# ========================================================

os.makedirs(DOSSIER_BASES, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

FICHIER_CACHE = os.path.join(DATA_DIR, "cache.json")
FICHIER_PANIERS = os.path.join(DATA_DIR, "paniers.json")
FICHIER_TRANSACTIONS = os.path.join(DATA_DIR, "transactions.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ Gestion du cache ------------------
def charger_cache():
    if os.path.exists(FICHIER_CACHE):
        with open(FICHIER_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def sauvegarder_cache(cache):
    with open(FICHIER_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def mettre_a_jour_cache():
    fichiers = glob.glob(os.path.join(DOSSIER_BASES, "*.txt"))
    cache = {}
    for chemin in fichiers:
        nom_fichier = os.path.basename(chemin)
        try:
            with open(chemin, 'r', encoding='utf-8') as f:
                lignes = [l.strip() for l in f if l.strip()]
            cache[nom_fichier] = {
                "nom": nom_fichier.replace('.txt', '').replace('_', ' ').title(),
                "lignes": len(lignes),
                "chemin": chemin
            }
        except Exception as e:
            logger.error(f"Erreur lecture {chemin}: {e}")
    sauvegarder_cache(cache)
    return cache

def get_bases():
    cache = charger_cache()
    if not cache:
        cache = mettre_a_jour_cache()
    return cache

# ------------------ Gestion du panier ------------------
def charger_paniers():
    if os.path.exists(FICHIER_PANIERS):
        with open(FICHIER_PANIERS, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def sauvegarder_paniers(paniers):
    with open(FICHIER_PANIERS, 'w', encoding='utf-8') as f:
        json.dump(paniers, f, indent=2, ensure_ascii=False)

def get_panier(user_id):
    paniers = charger_paniers()
    uid = str(user_id)
    if uid not in paniers:
        paniers[uid] = {"items": [], "total": 0}
        sauvegarder_paniers(paniers)
    return paniers[uid]

def ajouter_au_panier(user_id, fichier, qte_mille, prix_unitaire, nom):
    paniers = charger_paniers()
    uid = str(user_id)
    if uid not in paniers:
        paniers[uid] = {"items": [], "total": 0}
    for item in paniers[uid]["items"]:
        if item["fichier"] == fichier:
            item["quantite"] += qte_mille
            item["prix_total"] = item["quantite"] * prix_unitaire
            break
    else:
        paniers[uid]["items"].append({
            "fichier": fichier,
            "nom": nom,
            "quantite": qte_mille,
            "prix_unitaire": prix_unitaire,
            "prix_total": qte_mille * prix_unitaire
        })
    paniers[uid]["total"] = sum(i["prix_total"] for i in paniers[uid]["items"])
    sauvegarder_paniers(paniers)

def retirer_du_panier(user_id, fichier):
    paniers = charger_paniers()
    uid = str(user_id)
    if uid in paniers:
        paniers[uid]["items"] = [i for i in paniers[uid]["items"] if i["fichier"] != fichier]
        paniers[uid]["total"] = sum(i["prix_total"] for i in paniers[uid]["items"])
        sauvegarder_paniers(paniers)

def vider_panier(user_id):
    paniers = charger_paniers()
    uid = str(user_id)
    if uid in paniers:
        paniers[uid] = {"items": [], "total": 0}
        sauvegarder_paniers(paniers)

# ------------------ Fonctions de prise de lignes ------------------
def prendre_lignes(fichier, quantite):
    cache = get_bases()
    if fichier not in cache:
        return None
    chemin = cache[fichier]["chemin"]
    with open(chemin, 'r', encoding='utf-8') as f:
        toutes = [l.strip() for l in f if l.strip()]
    if len(toutes) < quantite:
        return None
    prises = toutes[:quantite]
    restantes = toutes[quantite:]
    with open(chemin, 'w', encoding='utf-8') as f:
        f.write("\n".join(restantes))
    cache[fichier]["lignes"] = len(restantes)
    sauvegarder_cache(cache)
    return prises

# ------------------ Taux de change ------------------
def obtenir_taux(devise):
    """Récupère le taux de change actuel EUR → crypto via CoinGecko."""
    try:
        if devise == "BTC":
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur"
        elif devise == "ETH":
            url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=eur"
        elif devise == "SOL":
            url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=eur"
        else:
            return None
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if devise == "BTC":
                return 1 / data['bitcoin']['eur']
            elif devise == "ETH":
                return 1 / data['ethereum']['eur']
            elif devise == "SOL":
                return 1 / data['solana']['eur']
    except Exception as e:
        logger.error(f"Erreur taux {devise}: {e}")
    
    # Taux de secours (approximatifs)
    return {"BTC": 0.000016, "ETH": 0.0003, "SOL": 0.05}[devise]

# ------------------ Vérification des transactions ------------------
def charger_transactions():
    if os.path.exists(FICHIER_TRANSACTIONS):
        with open(FICHIER_TRANSACTIONS, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def sauvegarder_transactions(transactions):
    with open(FICHIER_TRANSACTIONS, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, indent=2, ensure_ascii=False)

def verifier_transaction_btc(adresse, montant_attendu):
    """Vérifie via Blockstream si une transaction BTC a été reçue."""
    try:
        url = f"https://blockstream.info/api/address/{adresse}/txs"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            txs = response.json()
            for tx in txs:
                for output in tx.get('vout', []):
                    if 'scriptpubkey_address' in output and output['scriptpubkey_address'] == adresse:
                        valeur_btc = output['value'] / 100_000_000
                        if valeur_btc >= montant_attendu * 0.99:
                            if tx.get('status', {}).get('confirmed'):
                                return True, tx['txid']
        return False, None
    except Exception as e:
        logger.error(f"Erreur vérification BTC: {e}")
        return False, None

def verifier_transaction_eth(adresse, montant_attendu):
    """Vérifie via Etherscan si une transaction ETH a été reçue."""
    try:
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={adresse}&sort=desc&apikey={ETHERSCAN_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1':
                for tx in data['result']:
                    if tx['to'].lower() == adresse.lower() and tx['txreceipt_status'] == '1':
                        valeur_eth = int(tx['value']) / 10**18
                        if valeur_eth >= montant_attendu * 0.99:
                            return True, tx['hash']
        return False, None
    except Exception as e:
        logger.error(f"Erreur vérification ETH: {e}")
        return False, None

def verifier_transaction_sol(adresse, montant_attendu):
    """Vérifie via Solscan si une transaction SOL a été reçue."""
    try:
        url = f"https://api.solscan.io/account/transactions?account={adresse}&limit=10"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for tx in data.get('data', []):
                if tx.get('status') == 'Success':
                    for token in tx.get('tokenTransfers', []):
                        if token.get('destination') == adresse:
                            valeur_sol = token.get('amount', 0) / 10**9
                            if valeur_sol >= montant_attendu * 0.99:
                                return True, tx['txHash']
        return False, None
    except Exception as e:
        logger.error(f"Erreur vérification SOL: {e}")
        return False, None

async def verifier_et_livrer(context: ContextTypes.DEFAULT_TYPE):
    """Vérifie les transactions en attente et livre si confirmé."""
    transactions = charger_transactions()
    nouvelles = []
    
    for tx_id, data in transactions.items():
        if data['statut'] == 'en_attente':
            # Vérifier selon la devise
            if data['devise'] == 'BTC':
                taux = obtenir_taux('BTC')
                montant_crypto_attendu = data['montant_euro'] * taux
                ok, tx_hash = verifier_transaction_btc(data['adresse'], montant_crypto_attendu)
            elif data['devise'] == 'ETH':
                taux = obtenir_taux('ETH')
                montant_crypto_attendu = data['montant_euro'] * taux
                ok, tx_hash = verifier_transaction_eth(data['adresse'], montant_crypto_attendu)
            elif data['devise'] == 'SOL':
                taux = obtenir_taux('SOL')
                montant_crypto_attendu = data['montant_euro'] * taux
                ok, tx_hash = verifier_transaction_sol(data['adresse'], montant_crypto_attendu)
            else:
                continue
            
            if ok:
                # Paiement confirmé, livrer
                user_id = data['user_id']
                items = data['items']
                
                # Vérifier le stock
                stock_ok = True
                for item in items:
                    fichier = item["fichier"]
                    quantite = item["quantite"] * 1000
                    cache = get_bases()
                    if fichier not in cache or cache[fichier]["lignes"] < quantite:
                        stock_ok = False
                        break
                
                if stock_ok:
                    toutes = []
                    for item in items:
                        prises = prendre_lignes(item["fichier"], item["quantite"] * 1000)
                        if prises:
                            toutes.extend(prises)
                    
                    vider_panier(user_id)
                    
                    # Envoyer le fichier
                    nom_fichier = f"achat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(nom_fichier, 'w', encoding='utf-8') as f:
                        f.write("\n".join(toutes))
                    
                    # Envoyer à l'utilisateur
                    with open(nom_fichier, 'rb') as f:
                        await context.bot.send_document(
                            chat_id=user_id,
                            document=f,
                            filename=nom_fichier,
                            caption=f"✅ Paiement confirmé ! Transaction : {tx_hash}"
                        )
                    os.remove(nom_fichier)
                    
                    data['statut'] = 'livre'
                    # Notifier l'admin
                    for admin in ADMIN_IDS:
                        try:
                            montant_euro = data['montant_euro']
                            pourcent = ADMINS[0]['pourcentage'] if ADMINS else 100
                            await context.bot.send_message(
                                chat_id=admin,
                                text=f"💰 Vente réalisée : {montant_euro}€ en {data['devise']}\nClient: {user_id}"
                            )
                        except:
                            pass
                else:
                    data['statut'] = 'erreur_stock'
            
            # Expiration après 2 heures
            if datetime.fromisoformat(data['date']) + timedelta(hours=2) < datetime.now():
                data['statut'] = 'expire'
        
        nouvelles.append((tx_id, data))
    
    # Sauvegarder les mises à jour
    sauvegarder_transactions({k: v for k, v in nouvelles})

# ------------------ Affichage du menu principal ------------------
def get_main_keyboard(user_id):
    panier = get_panier(user_id)
    keyboard = []
    if panier["items"]:
        for item in panier["items"]:
            keyboard.append([InlineKeyboardButton(
                f"❌ Retirer {item['nom']} ({item['quantite']}k - {item['prix_total']}€",
                callback_data=f"remove_{item['fichier']}"
            )])
        keyboard.append([
            InlineKeyboardButton("💳 Payer", callback_data="payer"),
            InlineKeyboardButton("🗑️ Vider", callback_data="vider")
        ])
    bases = get_bases()
    for fichier, infos in bases.items():
        keyboard.append([InlineKeyboardButton(
            f"{infos['nom']} ({infos['lignes']} lignes dispo)",
            callback_data=f"base_{fichier}"
        )])
    return InlineKeyboardMarkup(keyboard)

# ------------------ Handlers ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    panier = get_panier(user_id)
    msg = f"{WELCOME_MSG}\n\n"
    if panier["items"]:
        msg += "**Votre panier :**\n"
        for item in panier["items"]:
            msg += f"• {item['nom']} : {item['quantite']}k = {item['prix_total']}€\n"
        msg += f"💰 **Total : {panier['total']}€**\n\n"
    msg += "Choisissez une base :"
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    logger.info(f"Data reçue : {data}")

    if data == "noop":
        return

    # --- Sélection d'une base ---
    if data.startswith("base_"):
        fichier = data.replace("base_", "")
        bases = get_bases()
        if fichier not in bases:
            await query.edit_message_text("Base introuvable.")
            return
        context.user_data["fichier"] = fichier
        context.user_data["nom"] = bases[fichier]["nom"]
        context.user_data["stock"] = bases[fichier]["lignes"]
        context.user_data["qte"] = 1
        await afficher_quantite(query, context)

    # --- Boutons de quantité ---
    elif data == "qte_plus":
        q = context.user_data["qte"]
        max_q = context.user_data["stock"] // 1000
        if q < max_q:
            context.user_data["qte"] += 1
        await afficher_quantite(query, context)

    elif data == "qte_moins":
        q = context.user_data["qte"]
        if q > 1:
            context.user_data["qte"] -= 1
        await afficher_quantite(query, context)

    # --- Ajouter au panier ---
    elif data == "ajouter":
        fichier = context.user_data["fichier"]
        qte = context.user_data["qte"]
        nom = context.user_data["nom"]
        ajouter_au_panier(user_id, fichier, qte, PRIX_PAR_MILLE, nom)
        await retour_accueil(query, user_id, f"✅ {nom} {qte}k ajouté au panier.")

    # --- Retirer du panier ---
    elif data.startswith("remove_"):
        fichier = data.replace("remove_", "")
        retirer_du_panier(user_id, fichier)
        await retour_accueil(query, user_id, "Article retiré.")

    # --- Vider le panier ---
    elif data == "vider":
        vider_panier(user_id)
        await retour_accueil(query, user_id, "Panier vidé.")

    # --- Payer ---
    elif data == "payer":
        panier = get_panier(user_id)
        if not panier["items"]:
            await query.edit_message_text("Votre panier est vide.")
            return
        context.user_data["montant_total"] = panier["total"]
        context.user_data["panier_a_payer"] = panier["items"].copy()
        keyboard = [
            [InlineKeyboardButton("₿ BTC", callback_data="devise_BTC")],
            [InlineKeyboardButton("Ξ ETH", callback_data="devise_ETH")],
            [InlineKeyboardButton("◎ SOL", callback_data="devise_SOL")],
            [InlineKeyboardButton("◀️ Retour", callback_data="retour")]
        ]
        await query.edit_message_text(
            f"Montant total : **{panier['total']}€**\nChoisissez votre devise :",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # --- Choix de la devise ---
    elif data.startswith("devise_"):
        devise = data.replace("devise_", "").upper()
        montant = context.user_data.get("montant_total")
        if not montant:
            await query.edit_message_text("Erreur, recommencez.")
            return
        
        # Obtenir le taux et calculer le montant en crypto
        taux = obtenir_taux(devise)
        montant_crypto = round(montant * taux, 8)
        
        # Sélectionner l'adresse
        if devise == "BTC":
            adresse = TA_ADRESSE_BTC
        elif devise == "ETH":
            adresse = TA_ADRESSE_ETH
        else:
            adresse = TA_ADRESSE_SOL
        
        # Générer un ID de transaction unique
        tx_id = f"{user_id}_{int(time.time())}"
        
        # Sauvegarder la transaction en attente
        transactions = charger_transactions()
        transactions[tx_id] = {
            "user_id": user_id,
            "devise": devise,
            "montant_euro": montant,
            "montant_crypto": montant_crypto,
            "adresse": adresse,
            "items": context.user_data["panier_a_payer"],
            "date": datetime.now().isoformat(),
            "statut": "en_attente"
        }
        sauvegarder_transactions(transactions)
        
        msg = (f"💰 Montant total : **{montant} €**\n"
               f"Ce qui équivaut à environ **{montant_crypto} {devise}** (taux actuel).\n\n"
               f"Veuillez envoyer **{montant_crypto} {devise}** à l'adresse suivante :\n"
               f"`{adresse}`\n\n"
               f"⏳ La vérification est automatique. Vous recevrez vos fichiers dès confirmation sur la blockchain.\n"
               f"ID transaction : `{tx_id}`")
        
        keyboard = [[InlineKeyboardButton("◀️ Retour", callback_data="retour")]]
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    # --- Retour à l'accueil ---
    elif data == "retour":
        await retour_accueil(query, user_id)

async def afficher_quantite(query, context):
    nom = context.user_data["nom"]
    stock = context.user_data["stock"]
    qte = context.user_data["qte"]
    keyboard = [
        [
            InlineKeyboardButton("-1", callback_data="qte_moins"),
            InlineKeyboardButton(f"{qte}k", callback_data="noop"),
            InlineKeyboardButton("+1", callback_data="qte_plus")
        ],
        [InlineKeyboardButton("✅ Ajouter au panier", callback_data="ajouter")],
        [InlineKeyboardButton("◀️ Retour", callback_data="retour")]
    ]
    await query.edit_message_text(
        f"Base : **{nom}**\nStock : {stock} lignes\n\n"
        f"Quantité : {qte} millier(s) ({qte*1000} lignes)\n"
        f"Prix : {qte * PRIX_PAR_MILLE}€",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def retour_accueil(query, user_id, message_supp=None):
    panier = get_panier(user_id)
    msg = f"{WELCOME_MSG}\n\n"
    if message_supp:
        msg += message_supp + "\n\n"
    if panier["items"]:
        msg += "**Votre panier :**\n"
        for item in panier["items"]:
            msg += f"• {item['nom']} : {item['quantite']}k = {item['prix_total']}€\n"
        msg += f"💰 **Total : {panier['total']}€**\n\n"
    msg += "Choisissez une base :"
    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=get_main_keyboard(user_id))

# ------------------ Commandes admin ------------------
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Accès refusé.")
        return
    bases = get_bases()
    total = sum(b["lignes"] for b in bases.values())
    msg = f"📊 **Statistiques**\n\nBases : {len(bases)}\nLignes totales : {total}\n\n"
    for f, infos in bases.items():
        msg += f"• {infos['nom']} : {infos['lignes']} lignes\n"
    
    # Ajouter les stats des transactions
    transactions = charger_transactions()
    en_attente = sum(1 for t in transactions.values() if t['statut'] == 'en_attente')
    livrees = sum(1 for t in transactions.values() if t['statut'] == 'livre')
    msg += f"\n📦 Transactions en attente : {en_attente}\n✅ Transactions livrées : {livrees}"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def refresh_cache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Accès refusé.")
        return
    mettre_a_jour_cache()
    await update.message.reply_text("✅ Cache mis à jour.")

# ------------------ Main ------------------
def main():
    logger.info("Démarrage du bot...")
    try:
        mettre_a_jour_cache()
        logger.info("Cache initialisé.")
    except Exception as e:
        logger.error(f"Erreur cache: {e}")

    app = Application.builder().token(BOT_TOKEN).build()
    
    # Job de vérification toutes les 2 minutes
    job_queue = app.job_queue
    job_queue.run_repeating(verifier_et_livrer, interval=120, first=10)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_stats))
    app.add_handler(CommandHandler("refresh", refresh_cache))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot démarré avec vérification automatique...")
    app.run_polling()

if __name__ == "__main__":
    main()