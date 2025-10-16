import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config
from .checks import has_normal_role
import random
import asyncio
import json
import os
from datetime import datetime, timedelta

# Sistema de configuración de idioma
class LanguageSystem:
    def __init__(self):
        self.data_file = "language_data.json"
        self.data = self.load_data()
        
        # Textos en diferentes idiomas
        self.texts = {
            'es': {
                'casino_title': "🎰 Casino Infinity RB",
                'balance': "Balance",
                'cash': "Efectivo",
                'bank': "Banco",
                'total': "Total",
                'deposit': "Depositar",
                'withdraw': "Retirar",
                'bet': "Apuesta",
                'win': "Ganaste",
                'lose': "Perdiste",
                'profit': "Ganancia",
                'current_balance': "Balance actual",
                'invalid_number': "Por favor ingresa un número válido",
                'insufficient_funds': "No tienes suficiente dinero",
                'bank_success': "Operación Bancaria Exitosa",
                'slots': "Tragaperras",
                'dice': "Dados",
                'roulette': "Ruleta",
                'blackjack': "Blackjack"
            },
            'en': {
                'casino_title': "🎰 Infinity RB Casino",
                'balance': "Balance",
                'cash': "Cash",
                'bank': "Bank",
                'total': "Total",
                'deposit': "Deposit",
                'withdraw': "Withdraw",
                'bet': "Bet",
                'win': "You won",
                'lose': "You lost",
                'profit': "Profit",
                'current_balance': "Current balance",
                'invalid_number': "Please enter a valid number",
                'insufficient_funds': "You don't have enough money",
                'bank_success': "Bank Operation Successful",
                'slots': "Slots",
                'dice': "Dice",
                'roulette': "Roulette",
                'blackjack': "Blackjack"
            }
        }
    
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def get_language(self, user_id):
        return self.data.get(str(user_id), 'es')
    
    def set_language(self, user_id, language):
        self.data[str(user_id)] = language
        self.save_data()
    
    def get_text(self, user_id, key):
        lang = self.get_language(user_id)
        return self.texts[lang].get(key, key)

# Sistema de economía del casino
class CasinoEconomy:
    def __init__(self, language_system):
        self.data_file = "casino_data.json"
        self.language = language_system
        self.data = self.load_data()
        self.work_cooldowns = {}
    
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def get_balance(self, user_id):
        return self.data.get(str(user_id), {"balance": 1000, "bank": 0, "daily_claimed": None})
    
    def update_balance(self, user_id, balance_change=0, bank_change=0):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = {"balance": 1000, "bank": 0, "daily_claimed": None}
        
        self.data[user_id]["balance"] = max(0, self.data[user_id]["balance"] + balance_change)
        self.data[user_id]["bank"] = max(0, self.data[user_id]["bank"] + bank_change)
        self.save_data()
    
    def can_claim_daily(self, user_id):
        user_data = self.get_balance(user_id)
        if not user_data["daily_claimed"]:
            return True
        
        last_claim = datetime.fromisoformat(user_data["daily_claimed"])
        return datetime.now() - last_claim > timedelta(hours=24)
    
    def claim_daily(self, user_id):
        if self.can_claim_daily(user_id):
            amount = random.randint(100, 500)
            self.update_balance(user_id, balance_change=amount)
            self.data[str(user_id)]["daily_claimed"] = datetime.now().isoformat()
            self.save_data()
            return amount
        return 0
    
    def can_work(self, user_id):
        user_id_str = str(user_id)
        if user_id_str not in self.work_cooldowns:
            return True
        return datetime.now() - self.work_cooldowns[user_id_str] > timedelta(minutes=5)
    
    def set_work_cooldown(self, user_id):
        self.work_cooldowns[str(user_id)] = datetime.now()

# Clase para el juego de Blackjack
class BlackjackGame:
    def __init__(self):
        self.deck = []
        self.player_hand = []
        self.dealer_hand = []
        self.reset_deck()
    
    def reset_deck(self):
        # Crear un mazo de 52 cartas
        suits = ['♠', '♥', '♦', '♣']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [f"{value}{suit}" for suit in suits for value in values]
        random.shuffle(self.deck)
    
    def deal_card(self):
        if len(self.deck) < 10:  # Si quedan pocas cartas, resetear el mazo
            self.reset_deck()
        return self.deck.pop()
    
    def calculate_hand_value(self, hand):
        value = 0
        aces = 0
        
        for card in hand:
            rank = card[:-1]  # Remover el palo
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                value += 11
                aces += 1
            else:
                value += int(rank)
        
        # Ajustar valor de los Ases si es necesario
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def start_game(self):
        self.player_hand = [self.deal_card(), self.deal_card()]
        self.dealer_hand = [self.deal_card(), self.deal_card()]
    
    def player_hit(self):
        self.player_hand.append(self.deal_card())
        return self.calculate_hand_value(self.player_hand)
    
    def dealer_play(self):
        while self.calculate_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deal_card())
        return self.calculate_hand_value(self.dealer_hand)
    
    def get_game_state(self, show_dealer_card=False):
        player_value = self.calculate_hand_value(self.player_hand)
        dealer_value = self.calculate_hand_value(self.dealer_hand)
        
        player_hand_str = " ".join(self.player_hand)
        if show_dealer_card:
            dealer_hand_str = " ".join(self.dealer_hand)
        else:
            dealer_hand_str = f"{self.dealer_hand[0]} 🂠"
        
        return {
            'player_hand': player_hand_str,
            'dealer_hand': dealer_hand_str,
            'player_value': player_value,
            'dealer_value': dealer_value if show_dealer_card else "?"
        }

class BlackjackView(discord.ui.View):
    def __init__(self, game, bet, economy, language_system, user_id):
        super().__init__(timeout=60)
        self.game = game
        self.bet = bet
        self.economy = economy
        self.language = language_system
        self.user_id = user_id
        self.game_over = False
    
    @discord.ui.button(label='Pedir Carta', style=discord.ButtonStyle.primary, emoji='🃏')
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Este juego no es tuyo!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Este juego ya terminó!", ephemeral=True)
            return
        
        # Jugador pide carta
        player_value = self.game.player_hit()
        state = self.game.get_game_state()
        
        if player_value > 21:
            # Jugador se pasa de 21
            self.game_over = True
            final_state = self.game.get_game_state(show_dealer_card=True)
            self.economy.update_balance(self.user_id, balance_change=-self.bet)
            
            embed = discord.Embed(
                title="🃏 Blackjack - Resultado Final",
                color=config.BOT_COLORS["error"]
            )
            embed.add_field(name="🤵 Tu Mano", value=f"{final_state['player_hand']}\n**Valor: {final_state['player_value']}**", inline=False)
            embed.add_field(name="💼 Mano del Dealer", value=f"{final_state['dealer_hand']}\n**Valor: {final_state['dealer_value']}**", inline=False)
            embed.add_field(name="💰 Resultado", value=f"❌ **Te pasaste de 21!**\n**Pérdida:** -{self.bet}", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=None)
        
        else:
            # Actualizar estado del juego
            embed = discord.Embed(
                title="🃏 Blackjack - En Progreso",
                color=config.BOT_COLORS["primary"]
            )
            embed.add_field(name="🤵 Tu Mano", value=f"{state['player_hand']}\n**Valor: {state['player_value']}**", inline=False)
            embed.add_field(name="💼 Mano del Dealer", value=f"{state['dealer_hand']}\n**Valor: {state['dealer_value']}**", inline=False)
            embed.add_field(name="💰 Apuesta", value=f"```{self.bet}```", inline=True)
            
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='Plantarse', style=discord.ButtonStyle.success, emoji='✋')
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Este juego no es tuyo!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Este juego ya terminó!", ephemeral=True)
            return
        
        self.game_over = True
        
        # Dealer juega
        dealer_value = self.game.dealer_play()
        player_value = self.game.calculate_hand_value(self.game.player_hand)
        final_state = self.game.get_game_state(show_dealer_card=True)
        
        # Determinar resultado
        if dealer_value > 21:
            # Dealer se pasa, jugador gana
            result = "win"
            payout = self.bet * 2
            result_text = f"✅ **Dealer se pasó! Ganas**\n**Ganancia:** +{self.bet}"
            self.economy.update_balance(self.user_id, balance_change=self.bet)
        elif dealer_value > player_value:
            # Dealer gana
            result = "lose"
            payout = 0
            result_text = f"❌ **Dealer gana!**\n**Pérdida:** -{self.bet}"
            self.economy.update_balance(self.user_id, balance_change=-self.bet)
        elif player_value > dealer_value:
            # Jugador gana
            result = "win"
            payout = self.bet * 2
            result_text = f"✅ **Ganas!**\n**Ganancia:** +{self.bet}"
            self.economy.update_balance(self.user_id, balance_change=self.bet)
        else:
            # Empate
            result = "push"
            payout = self.bet
            result_text = f"🤝 **Empate!**\n**Recuperas tu apuesta**"
            # No se cambia el balance
        
        color = config.BOT_COLORS["success"] if result == "win" else config.BOT_COLORS["error"] if result == "lose" else config.BOT_COLORS["warning"]
        
        embed = discord.Embed(
            title="🃏 Blackjack - Resultado Final",
            color=color
        )
        embed.add_field(name="🤵 Tu Mano", value=f"{final_state['player_hand']}\n**Valor: {final_state['player_value']}**", inline=False)
        embed.add_field(name="💼 Mano del Dealer", value=f"{final_state['dealer_hand']}\n**Valor: {final_state['dealer_value']}**", inline=False)
        embed.add_field(name="💰 Resultado", value=result_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)

class BlackjackModal(discord.ui.Modal, title='🃏 Blackjack'):
    def __init__(self, economy, language_system):
        super().__init__()
        self.economy = economy
        self.language = language_system
    
    bet_amount = discord.ui.TextInput(
        label='Cantidad a apostar',
        placeholder='Ej: 100, 500, 1000...',
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(self.bet_amount.value)
            user_data = self.economy.get_balance(interaction.user.id)
            
            if bet <= 0:
                await interaction.response.send_message("❌ La apuesta debe ser mayor a 0.", ephemeral=True)
                return
            
            if user_data["balance"] < bet:
                await interaction.response.send_message(f"❌ No tienes suficiente dinero. Balance: 💰{user_data['balance']}", ephemeral=True)
                return
            
            # Iniciar juego de Blackjack
            game = BlackjackGame()
            game.start_game()
            state = game.get_game_state()
            
            embed = discord.Embed(
                title="🃏 Blackjack - En Progreso",
                color=config.BOT_COLORS["primary"]
            )
            embed.add_field(name="🤵 Tu Mano", value=f"{state['player_hand']}\n**Valor: {state['player_value']}**", inline=False)
            embed.add_field(name="💼 Mano del Dealer", value=f"{state['dealer_hand']}\n**Valor: {state['dealer_value']}**", inline=False)
            embed.add_field(name="💰 Apuesta", value=f"```{bet}```", inline=True)
            embed.add_field(name="🎯 Acciones", value="**Pedir Carta**: Recibir otra carta\n**Plantarse**: Terminar tu turno", inline=False)
            
            view = BlackjackView(game, bet, self.economy, self.language, interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Por favor ingresa un número válido.", ephemeral=True)

class CasinoView(discord.ui.View):
    def __init__(self, bot, economy, language_system):
        super().__init__(timeout=300)
        self.bot = bot
        self.economy = economy
        self.language = language_system
    
    @discord.ui.button(label='🎰 Tragaperras', style=discord.ButtonStyle.primary, emoji='🎰')
    async def slots(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SlotsModal(self.economy, self.language))
    
    @discord.ui.button(label='🎯 Dados', style=discord.ButtonStyle.primary, emoji='🎯')
    async def dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DiceModal(self.economy, self.language))
    
    @discord.ui.button(label='🎪 Ruleta', style=discord.ButtonStyle.success, emoji='🎪')
    async def roulette(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RouletteModal(self.economy, self.language))
    
    @discord.ui.button(label='🃏 Blackjack', style=discord.ButtonStyle.danger, emoji='🃏')
    async def blackjack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BlackjackModal(self.economy, self.language))
    
    @discord.ui.button(label='💰 Banco', style=discord.ButtonStyle.secondary, emoji='💰')
    async def bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BankModal(self.economy, self.language))

class SlotsModal(discord.ui.Modal, title='🎰 Tragaperras'):
    def __init__(self, economy, language_system):
        super().__init__()
        self.economy = economy
        self.language = language_system
    
    bet_amount = discord.ui.TextInput(
        label='Cantidad a apostar',
        placeholder='Ej: 100, 500, 1000...',
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(self.bet_amount.value)
            user_data = self.economy.get_balance(interaction.user.id)
            lang = self.language.get_language(interaction.user.id)
            
            if bet <= 0:
                await interaction.response.send_message("❌ La apuesta debe ser mayor a 0.", ephemeral=True)
                return
            
            if user_data["balance"] < bet:
                await interaction.response.send_message(f"❌ No tienes suficiente dinero. Balance: 💰{user_data['balance']}", ephemeral=True)
                return
            
            # Jugar a las tragaperras
            symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎', '7️⃣']
            result = [random.choice(symbols) for _ in range(3)]
            
            # Calcular ganancias
            payout = 0
            if result[0] == result[1] == result[2]:
                if result[0] == '7️⃣':
                    payout = bet * 10
                elif result[0] == '💎':
                    payout = bet * 5
                else:
                    payout = bet * 3
            elif result[0] == result[1] or result[1] == result[2]:
                payout = bet * 1.5
            
            # Actualizar balance
            net_gain = payout - bet
            self.economy.update_balance(interaction.user.id, balance_change=net_gain)
            
            win_text = self.language.get_text(interaction.user.id, 'win') if payout > 0 else self.language.get_text(interaction.user.id, 'lose')
            
            embed = discord.Embed(
                title="🎰 Tragaperras",
                description=f"**Resultado:** {' | '.join(result)}",
                color=config.BOT_COLORS["primary"]
            )
            
            embed.add_field(name="💰 Apuesta", value=f"```{bet}```", inline=True)
            embed.add_field(name="🎯 Resultado", value=f"```{win_text}```", inline=True)
            embed.add_field(name="💸 Ganancia", value=f"```{net_gain}```", inline=True)
            
            embed.set_footer(text=f"Balance actual: 💰{user_data['balance'] + net_gain}")
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Por favor ingresa un número válido.", ephemeral=True)

class DiceModal(discord.ui.Modal, title='🎯 Juego de Dados'):
    def __init__(self, economy, language_system):
        super().__init__()
        self.economy = economy
        self.language = language_system
    
    bet_amount = discord.ui.TextInput(
        label='Cantidad a apostar',
        placeholder='Ej: 100, 500, 1000...',
        required=True
    )
    
    prediction = discord.ui.TextInput(
        label='Tu predicción (2-12)',
        placeholder='Ej: 7, 11, 2...',
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(self.bet_amount.value)
            user_prediction = int(self.prediction.value)
            user_data = self.economy.get_balance(interaction.user.id)
            
            if bet <= 0:
                await interaction.response.send_message("❌ La apuesta debe ser mayor a 0.", ephemeral=True)
                return
            
            if user_data["balance"] < bet:
                await interaction.response.send_message(f"❌ No tienes suficiente dinero. Balance: 💰{user_data['balance']}", ephemeral=True)
                return
            
            if user_prediction < 2 or user_prediction > 12:
                await interaction.response.send_message("❌ La predicción debe estar entre 2 y 12.", ephemeral=True)
                return
            
            # Tirar dados
            dice1 = random.randint(1, 6)
            dice2 = random.randint(1, 6)
            total = dice1 + dice2
            
            # Calcular ganancias
            if user_prediction == total:
                payout = bet * 6
            elif abs(user_prediction - total) <= 2:
                payout = bet * 2
            else:
                payout = 0
            
            # Actualizar balance
            net_gain = payout - bet
            self.economy.update_balance(interaction.user.id, balance_change=net_gain)
            
            embed = discord.Embed(
                title="🎯 Juego de Dados",
                description=f"**Tirada:** 🎲 {dice1} + 🎲 {dice2} = **{total}**",
                color=config.BOT_COLORS["primary"]
            )
            
            embed.add_field(name="💰 Apuesta", value=f"```{bet}```", inline=True)
            embed.add_field(name="🎯 Predicción", value=f"```{user_prediction}```", inline=True)
            embed.add_field(name="💸 Ganancia", value=f"```{net_gain}```", inline=True)
            
            embed.set_footer(text=f"Balance actual: 💰{user_data['balance'] + net_gain}")
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Por favor ingresa números válidos.", ephemeral=True)

class RouletteModal(discord.ui.Modal, title='🎪 Ruleta'):
    def __init__(self, economy, language_system):
        super().__init__()
        self.economy = economy
        self.language = language_system
    
    bet_amount = discord.ui.TextInput(
        label='Cantidad a apostar',
        placeholder='Ej: 100, 500, 1000...',
        required=True
    )
    
    color_choice = discord.ui.TextInput(
        label='Color (rojo/negro/verde)',
        placeholder='Ej: rojo, negro, verde...',
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(self.bet_amount.value)
            color_choice = self.color_choice.value.lower().strip()
            user_data = self.economy.get_balance(interaction.user.id)
            
            if bet <= 0:
                await interaction.response.send_message("❌ La apuesta debe ser mayor a 0.", ephemeral=True)
                return
            
            if user_data["balance"] < bet:
                await interaction.response.send_message(f"❌ No tienes suficiente dinero. Balance: 💰{user_data['balance']}", ephemeral=True)
                return
            
            if color_choice not in ['rojo', 'negro', 'verde']:
                await interaction.response.send_message("❌ Color no válido. Usa: rojo, negro o verde", ephemeral=True)
                return
            
            # Generar resultado de ruleta (0-36, 0 es verde, 1-18 rojo, 19-36 negro)
            result_number = random.randint(0, 36)
            
            if result_number == 0:
                result_color = 'verde'
                multiplier = 14  # Pago 14:1 para verde
            elif 1 <= result_number <= 18:
                result_color = 'rojo'
                multiplier = 2   # Pago 2:1 para rojo/negro
            else:
                result_color = 'negro'
                multiplier = 2   # Pago 2:1 para rojo/negro
            
            # Calcular ganancias
            if color_choice == result_color:
                payout = bet * multiplier
                win = True
            else:
                payout = 0
                win = False
            
            # Actualizar balance
            net_gain = payout - bet
            self.economy.update_balance(interaction.user.id, balance_change=net_gain)
            
            # Emojis para los colores
            color_emojis = {'rojo': '🔴', 'negro': '⚫', 'verde': '🟢'}
            
            embed = discord.Embed(
                title="🎪 Ruleta",
                description=f"**Resultado:** {color_emojis[result_color]} **{result_number} {result_color.upper()}**",
                color=config.BOT_COLORS["primary"]
            )
            
            embed.add_field(name="💰 Apuesta", value=f"```{bet} en {color_choice}```", inline=True)
            embed.add_field(name="🎯 Resultado", value=f"```{'🎉 Ganaste!' if win else '💥 Perdiste'}```", inline=True)
            embed.add_field(name="💸 Ganancia", value=f"```{net_gain}```", inline=True)
            
            embed.add_field(
                name="📊 Multiplicadores",
                value="**Rojo/Negro:** 2x\n**Verde (0):** 14x",
                inline=False
            )
            
            embed.set_footer(text=f"Balance actual: 💰{user_data['balance'] + net_gain}")
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Por favor ingresa una cantidad válida.", ephemeral=True)

class BankModal(discord.ui.Modal, title='💰 Banco'):
    def __init__(self, economy, language_system):
        super().__init__()
        self.economy = economy
        self.language = language_system
    
    action = discord.ui.TextInput(
        label='Acción (depositar/retirar)',
        placeholder='Ej: depositar, retirar...',
        required=True
    )
    
    amount = discord.ui.TextInput(
        label='Cantidad',
        placeholder='Ej: 100, 500, 1000...',
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            action = self.action.value.lower()
            amount = int(self.amount.value)
            user_data = self.economy.get_balance(interaction.user.id)
            
            if amount <= 0:
                await interaction.response.send_message("❌ La cantidad debe ser mayor a 0.", ephemeral=True)
                return
            
            if action == "depositar":
                if user_data["balance"] < amount:
                    await interaction.response.send_message(f"❌ No tienes suficiente dinero en efectivo. Balance: 💰{user_data['balance']}", ephemeral=True)
                    return
                self.economy.update_balance(interaction.user.id, balance_change=-amount, bank_change=amount)
                message = f"✅ Has depositado 💰{amount} en el banco."
            
            elif action == "retirar":
                if user_data["bank"] < amount:
                    await interaction.response.send_message(f"❌ No tienes suficiente dinero en el banco. Banco: 🏦{user_data['bank']}", ephemeral=True)
                    return
                self.economy.update_balance(interaction.user.id, balance_change=amount, bank_change=-amount)
                message = f"✅ Has retirado 💰{amount} del banco."
            
            else:
                await interaction.response.send_message("❌ Acción no válida. Usa 'depositar' o 'retirar'.", ephemeral=True)
                return
            
            new_data = self.economy.get_balance(interaction.user.id)
            embed = discord.Embed(
                title="🏦 Operación Bancaria Exitosa",
                description=message,
                color=config.BOT_COLORS["success"]
            )
            
            embed.add_field(name="💰 Efectivo", value=f"```{new_data['balance']}```", inline=True)
            embed.add_field(name="🏦 Banco", value=f"```{new_data['bank']}```", inline=True)
            embed.add_field(name="📊 Total", value=f"```{new_data['balance'] + new_data['bank']}```", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Por favor ingresa una cantidad válida.", ephemeral=True)

class WorkQuestions:
    def __init__(self):
        self.questions = {
            '💻 Programador': [
                {"question": "¿Qué lenguaje usa 'print('Hola')'?", "options": ["Python", "Java", "C++", "JavaScript"], "answer": 0, "difficulty": "Fácil"},
                {"question": "¿Qué significa HTML?", "options": ["HyperText Markup Language", "HighTech Modern Language", "Hyper Transfer Markup Language", "HighText Mobile Language"], "answer": 0, "difficulty": "Medio"},
                {"question": "¿Qué patrón de diseño usa clases abstractas?", "options": ["Singleton", "Factory Method", "Observer", "Decorator"], "answer": 1, "difficulty": "Difícil"}
            ],
            '🍕 Repartidor': [
                {"question": "¿Cuál NO es un ingrediente de pizza?", "options": ["Pepperoni", "Chocolate", "Queso", "Tomate"], "answer": 1, "difficulty": "Fácil"},
                {"question": "¿Qué hacer si el cliente no contesta?", "options": ["Dejar la pizza", "Volver a la pizzería", "Llamar al supervisor", "Comer la pizza"], "answer": 2, "difficulty": "Medio"},
                {"question": "¿Cuál es la velocidad máxima en zona residencial?", "options": ["30 km/h", "50 km/h", "80 km/h", "100 km/h"], "answer": 1, "difficulty": "Difícil"}
            ],
            '🏪 Dependiente': [
                {"question": "¿Qué decir al cliente?", "options": ["¿Qué quieres?", "Hola, ¿en qué puedo ayudarle?", "Espérate", "No moleste"], "answer": 1, "difficulty": "Fácil"},
                {"question": "Un cliente devuelve producto sin ticket, ¿qué hacer?", "options": ["Aceptarlo igual", "Rechazar la devolución", "Consultar al supervisor", "Darle otro producto"], "answer": 2, "difficulty": "Medio"},
                {"question": "¿Qué porcentaje de IVA aplica a productos básicos?", "options": ["4%", "10%", "21%", "0%"], "answer": 0, "difficulty": "Difícil"}
            ],
            '🎨 Diseñador': [
                {"question": "¿Qué programa es para diseño vectorial?", "options": ["Photoshop", "Illustrator", "Premiere", "Excel"], "answer": 1, "difficulty": "Fácil"},
                {"question": "¿Qué significa RGB?", "options": ["Red Green Blue", "Real Good Background", "Random Graphic Balance", "Rapid Graphic Build"], "answer": 0, "difficulty": "Medio"},
                {"question": "¿Qué patrón de color usa CMYK?", "options": ["Aditivo", "Sustractivo", "Complementario", "Análogo"], "answer": 1, "difficulty": "Difícil"}
            ],
            '📊 Analista': [
                {"question": "¿Qué mide el ROI?", "options": ["Retorno de Inversión", "Rango de Operaciones Internas", "Ratio de Ocupación Instantánea", "Registro de Objetivos Importantes"], "answer": 0, "difficulty": "Fácil"},
                {"question": "¿Qué es un KPI?", "options": ["Key Performance Indicator", "Knowledge Process Integration", "Key Process Innovation", "Knowledge Performance Index"], "answer": 0, "difficulty": "Medio"},
                {"question": "¿Qué modelo predictivo usa árboles de decisión?", "options": ["Regresión lineal", "Random Forest", "K-means", "PCA"], "answer": 1, "difficulty": "Difícil"}
            ]
        }

class WorkView(discord.ui.View):
    def __init__(self, questions, job, economy):
        super().__init__(timeout=300)
        self.questions = questions
        self.job = job
        self.economy = economy
        self.answers = []
        self.current_question = 0
        self.display_question()
    
    def display_question(self):
        if self.current_question < len(self.questions):
            question_data = self.questions[self.current_question]
            self.clear_items()
            
            # Mostrar pregunta
            question_text = f"**{self.job} - Pregunta {self.current_question + 1} ({question_data['difficulty']})**\n{question_data['question']}"
            
            # Agregar botones para las opciones
            for i, option in enumerate(question_data['options']):
                self.add_item(WorkButton(option, i, question_data['answer']))
    
    async def handle_answer(self, interaction, selected, correct):
        self.answers.append(selected == correct)
        self.current_question += 1
        
        if self.current_question < len(self.questions):
            self.display_question()
            await interaction.response.edit_message(content=self.get_question_text(), view=self)
        else:
            # Calcular recompensa
            correct_answers = sum(self.answers)
            if correct_answers == 3:
                earnings = 500
            elif correct_answers == 2:
                earnings = 350
            elif correct_answers == 1:
                earnings = 150
            else:
                earnings = 50
            
            self.economy.update_balance(interaction.user.id, balance_change=earnings)
            self.economy.set_work_cooldown(interaction.user.id)
            
            result_text = f"**{self.job} - Resultado Final**\n"
            result_text += f"✅ Correctas: {correct_answers}/3\n"
            result_text += f"💰 Ganancia: {earnings}\n"
            result_text += f"🎯 Puntuación: {'⭐' * correct_answers}{'☆' * (3 - correct_answers)}"
            
            await interaction.response.edit_message(content=result_text, view=None)
    
    def get_question_text(self):
        if self.current_question < len(self.questions):
            question_data = self.questions[self.current_question]
            return f"**{self.job} - Pregunta {self.current_question + 1} ({question_data['difficulty']})**\n{question_data['question']}"
        return ""

class WorkButton(discord.ui.Button):
    def __init__(self, label, value, correct_answer):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.value = value
        self.correct_answer = correct_answer
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.handle_answer(interaction, self.value, self.correct_answer)

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.language_system = LanguageSystem()
        self.economy = CasinoEconomy(self.language_system)
        self.work_questions = WorkQuestions()
        
        # Comando !soy mejorado al estilo Nightbot
        self.soy_responses = [
            "fe@", "lind@", "guap@", "beboter@", "hermos@", "sex@", "precios@",
            "maravillos@", "fantástic@", "increíble", "espectacular", "divin@",
            "radiante", "magnífic@", "sensacional", "fabulos@", "estupend@",
            "genial", "fenomenal", "prodigios@", "extraordinari@", "asombros@"
        ]
        
        self.fun_responses = {
            'amor': ['💖 El amor está en el aire!', '❤️ Tu corazón late más rápido!', '💕 El amor lo puede todo!'],
            'odio': ['💔 El odio no lleva a nada bueno...', '😠 Calma, respira hondo...', '⚡ La ira consume energía!'],
            'triste': ['😔 Anímate! Todo mejorará', '🌈 Después de la tormenta siempre sale el sol', '🤗 Aquí tienes un abrazo virtual!'],
            'feliz': ['🎉 Qué bien! Sigue así!', '😊 La felicidad es contagiosa!', '⭐ Brillas con luz propia!'],
            'aburrido': ['🎮 Juega algo!', '🎵 Escucha música!', '🎬 Mira una película!', '📚 Lee un libro!'],
            'hambre': ['🍕 Pide una pizza!', '🍔 Hamburgesa time!', '🍣 Sushi siempre es buena idea!', '🌮 Tacos tacos tacos!'],
            'sueño': ['😴 A dormir!', '🛌 Descansa bien!', '💤 Zzzzz...', '🌙 Buenas noches!'],
            'enfadado': ['😤 Tranquilo, cuenta hasta 10', '⚡ No dejes que la ira te controle', '🌪️ Respira profundo!'],
            'emocionado': ['🚀 Wow! Qué emoción!', '🎊 Esto pinta bien!', '🔥 La adrenalina está alta!'],
            'confundido': ['🤔 Tómate tu tiempo', '🔍 Analiza bien la situación', '💡 La respuesta llegará!']
        }
    
    # COMANDOS DE IDIOMA
    @app_commands.command(name='idioma', description='Cambiar el idioma del bot (es/en)')
    @app_commands.describe(idioma="Idioma: es (Español) o en (English)")
    async def change_language(self, interaction: discord.Interaction, idioma: str):
        """Cambiar el idioma del bot"""
        if idioma.lower() not in ['es', 'en']:
            await interaction.response.send_message("❌ Idiomas disponibles: `es` (Español) o `en` (English)", ephemeral=True)
            return
        
        self.language_system.set_language(interaction.user.id, idioma.lower())
        
        if idioma.lower() == 'es':
            await interaction.response.send_message("✅ Idioma cambiado a **Español**")
        else:
            await interaction.response.send_message("✅ Language changed to **English**")
    
    # COMANDOS DE CASINO Y ECONOMÍA
    
    @app_commands.command(name='casino', description='Abrir el casino con juegos de azar')
    async def casino(self, interaction: discord.Interaction):
        """Panel del casino con diversos juegos"""
        user_data = self.economy.get_balance(interaction.user.id)
        lang = self.language_system.get_language(interaction.user.id)
        
        title = self.language_system.get_text(interaction.user.id, 'casino_title')
        cash_text = self.language_system.get_text(interaction.user.id, 'cash')
        bank_text = self.language_system.get_text(interaction.user.id, 'bank')
        total_text = self.language_system.get_text(interaction.user.id, 'total')
        
        embed = discord.Embed(
            title=title,
            description="**Bienvenido al casino!** Elige un juego para comenzar:\n\n"
                      "**🎰 Tragaperras** - Gira y gana\n"
                      "**🎯 Dados** - Adivina la tirada\n"
                      "**🎪 Ruleta** - Apuesta a colores\n"
                      "**🃏 Blackjack** - Juega contra el dealer\n"
                      "**💰 Banco** - Gestiona tu dinero",
            color=config.BOT_COLORS["primary"]
        )
        
        embed.add_field(
            name="💳 Tu Balance",
            value=f"**💰 {cash_text}:** {user_data['balance']}\n"
                  f"**🏦 {bank_text}:** {user_data['bank']}\n"
                  f"**📊 {total_text}:** {user_data['balance'] + user_data['bank']}",
            inline=False
        )
        
        embed.add_field(
            name="💡 Comandos Rápidos",
            value="`/balance` - Ver tu dinero\n`/daily` - Reclamar daily\n`/work` - Trabajar por dinero",
            inline=False
        )
        
        view = CasinoView(self.bot, self.economy, self.language_system)
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name='balance', description='Ver tu balance de dinero')
    @app_commands.describe(usuario="Usuario cuyo balance quieres ver (opcional)")
    async def balance(self, interaction: discord.Interaction, usuario: discord.Member = None):
        """Ver el balance de dinero"""
        target_user = usuario or interaction.user
        user_data = self.economy.get_balance(target_user.id)
        
        embed = discord.Embed(
            title=f"💳 Balance de {target_user.display_name}",
            color=config.BOT_COLORS["primary"]
        )
        
        embed.add_field(name="💰 Efectivo", value=f"```{user_data['balance']}```", inline=True)
        embed.add_field(name="🏦 Banco", value=f"```{user_data['bank']}```", inline=True)
        embed.add_field(name="📊 Total", value=f"```{user_data['balance'] + user_data['bank']}```", inline=True)
        
        # Verificar daily
        if target_user == interaction.user:
            if self.economy.can_claim_daily(interaction.user.id):
                embed.add_field(
                    name="🎁 Daily Disponible",
                    value="Usa `/daily` para reclamar tu recompensa diaria!",
                    inline=False
                )
            else:
                next_claim = datetime.fromisoformat(user_data["daily_claimed"]) + timedelta(hours=24)
                embed.add_field(
                    name="⏰ Próximo Daily",
                    value=f"Disponible: <t:{int(next_claim.timestamp())}:R>",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name='daily', description='Reclamar recompensa diaria')
    async def daily(self, interaction: discord.Interaction):
        """Reclamar recompensa diaria"""
        amount = self.economy.claim_daily(interaction.user.id)
        
        if amount > 0:
            embed = discord.Embed(
                title="🎁 Recompensa Diaria Reclamada!",
                description=f"Has recibido 💰**{amount}** de recompensa diaria!",
                color=config.BOT_COLORS["success"]
            )
            
            user_data = self.economy.get_balance(interaction.user.id)
            embed.add_field(name="💰 Nuevo Balance", value=f"```{user_data['balance']}```", inline=True)
            
            next_claim = datetime.now() + timedelta(hours=24)
            embed.set_footer(text=f"Próxima recompensa: {next_claim.strftime('%d/%m/%Y %H:%M')}")
            
            await interaction.response.send_message(embed=embed)
        else:
            user_data = self.economy.get_balance(interaction.user.id)
            next_claim = datetime.fromisoformat(user_data["daily_claimed"]) + timedelta(hours=24)
            
            embed = discord.Embed(
                title="⏰ Ya reclamaste hoy",
                description=f"Podrás reclamar nuevamente <t:{int(next_claim.timestamp())}:R>",
                color=config.BOT_COLORS["warning"]
            )
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name='work', description='Trabajar para ganar dinero respondiendo preguntas')
    async def work(self, interaction: discord.Interaction):
        """Trabajar para ganar dinero respondiendo preguntas"""
        if not self.economy.can_work(interaction.user.id):
            await interaction.response.send_message("⏰ **Debes esperar 5 minutos entre trabajos!**", ephemeral=True)
            return
        
        # Elegir trabajo aleatorio
        jobs = list(self.work_questions.questions.keys())
        job = random.choice(jobs)
        questions = self.work_questions.questions[job]
        
        # Enviar mensaje por DM
        try:
            # Enviar mensaje inicial por DM
            dm_message = await interaction.user.send(f"**{job} - Entrevista de Trabajo**\nResponde estas 3 preguntas correctamente para ganar dinero!")
            
            # Crear y enviar la vista de preguntas por DM
            view = WorkView(questions, job, self.economy)
            await interaction.user.send(view.get_question_text(), view=view)
            
            await interaction.response.send_message("📨 **Te he enviado las preguntas de trabajo por mensaje privado!**")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ **No puedo enviarte mensajes privados!** Activa los DMs para poder trabajar.", ephemeral=True)
    
    # COMANDOS DE DIVERSIÓN (SLASH) - CONVERTIDOS DE ! A /
    
    @app_commands.command(name='soy', description='Te dice algo bonito sobre ti')
    async def soy_command(self, interaction: discord.Interaction):
        """Comando soy mejorado al estilo Nightbot"""
        response = random.choice(self.soy_responses)
        await interaction.response.send_message(f"**{interaction.user.display_name}** es {response} 😉")
    
    @app_commands.command(name='decide', description='Decide entre opciones')
    @app_commands.describe(opciones="Opciones separadas por ' o ' (ej: pizza o hamburguesa)")
    async def decide_command(self, interaction: discord.Interaction, opciones: str):
        """Decide entre opciones"""
        # Separar por " o "
        choices = [opcion.strip() for opcion in opciones.split(' o ') if opcion.strip()]
        
        if len(choices) < 2:
            await interaction.response.send_message("❌ Necesitas al menos 2 opciones separadas por ' o '", ephemeral=True)
            return
        
        chosen = random.choice(choices)
        await interaction.response.send_message(f"🎯 **He decidido:** ```{chosen}```")
    
    @app_commands.command(name='dado', description='Tirar un dado')
    @app_commands.describe(caras="Número de caras del dado (por defecto 6)")
    async def dice_command(self, interaction: discord.Interaction, caras: int = 6):
        """Tirar un dado"""
        if caras < 2:
            await interaction.response.send_message("❌ El dado debe tener al menos 2 caras", ephemeral=True)
            return
        
        result = random.randint(1, caras)
        await interaction.response.send_message(f"🎲 **Dado de {caras} caras:** ```{result}```")
    
    @app_commands.command(name='bola8', description='Bola mágica 8')
    @app_commands.describe(pregunta="Tu pregunta para la bola mágica")
    async def eight_ball(self, interaction: discord.Interaction, pregunta: str):
        """Bola mágica 8"""
        respuestas = [
            "🎱 Sí, definitivamente", "🎱 Sin duda", "🎱 Absolutamente",
            "🎱 Probablemente", "🎱 Así parece", "🎱 Los signos apuntan a que sí",
            "🎱 No cuentes con ello", "🎱 Mis fuentes dicen que no",
            "🎱 Muy dudoso", "🎱 No", "🎱 Mejor no te lo digo ahora",
            "🎱 No puedo predecirlo ahora", "🎱 Concéntrate y pregunta again",
            "🎱 Pregunta más tarde", "🎱 La respuesta está en tu corazón"
        ]
        
        respuesta = random.choice(respuestas)
        await interaction.response.send_message(f"**{interaction.user.display_name} pregunta:** {pregunta}\n**🎱 Respuesta:** {respuesta}")
    
    @app_commands.command(name='abrazo', description='Dar un abrazo a un usuario')
    @app_commands.describe(usuario="Usuario al que quieres abrazar")
    async def hug_command(self, interaction: discord.Interaction, usuario: discord.Member):
        """Dar un abrazo"""
        if usuario == interaction.user:
            await interaction.response.send_message(f"🤗 **{interaction.user.display_name}** se abraza a sí mismo... un poco triste 😢")
            return
        
        mensajes = [
            f"🤗 **{interaction.user.display_name}** abraza fuertemente a **{usuario.display_name}**!",
            f"💕 **{interaction.user.display_name}** da un cálido abrazo a **{usuario.display_name}**!",
            f"🫂 **{interaction.user.display_name}** y **{usuario.display_name}** comparten un emotivo abrazo!",
            f"❤️ **{interaction.user.display_name}** abraza a **{usuario.display_name}** con mucho cariño!"
        ]
        
        await interaction.response.send_message(random.choice(mensajes))
    
    @app_commands.command(name='beso', description='Dar un beso a un usuario')
    @app_commands.describe(usuario="Usuario al que quieres besar")
    async def kiss_command(self, interaction: discord.Interaction, usuario: discord.Member):
        """Dar un beso"""
        if usuario == interaction.user:
            await interaction.response.send_message(f"💋 **{interaction.user.display_name}** se besa a sí mismo en el espejo... 😳")
            return
        
        mensajes = [
            f"💋 **{interaction.user.display_name}** le da un dulce beso a **{usuario.display_name}**!",
            f"😘 **{interaction.user.display_name}** besa apasionadamente a **{usuario.display_name}**!",
            f"💞 **{interaction.user.display_name}** y **{usuario.display_name}** comparten un beso romántico!",
            f"👩‍❤️‍💋‍👨 **{interaction.user.display_name}** roba un beso a **{usuario.display_name}**!"
        ]
        
        await interaction.response.send_message(random.choice(mensajes))
    
    @app_commands.command(name='gay', description='Medidor gay de un usuario')
    @app_commands.describe(usuario="Usuario a medir (opcional)")
    async def gay_command(self, interaction: discord.Interaction, usuario: discord.Member = None):
        """Medidor gay"""
        target = usuario or interaction.user
        percentage = random.randint(0, 100)
        
        # Crear barra de progreso
        bars = 10
        filled_bars = int(percentage / 100 * bars)
        bar = "🌈" * filled_bars + "⚫" * (bars - filled_bars)
        
        mensajes = [
            f"🏳️‍🌈 **{target.display_name}** es **{percentage}%** gay!\n{bar}",
            f"💖 **Medidor LGBTQ+** de **{target.display_name}**: **{percentage}%**\n{bar}",
            f"🎯 **Resultado del arcoíris**: **{target.display_name}** - **{percentage}%** gay\n{bar}"
        ]
        
        await interaction.response.send_message(random.choice(mensajes))
    
    @app_commands.command(name='simp', description='Medidor simp de un usuario')
    @app_commands.describe(usuario="Usuario a medir (opcional)")
    async def simp_command(self, interaction: discord.Interaction, usuario: discord.Member = None):
        """Medidor simp"""
        target = usuario or interaction.user
        percentage = random.randint(0, 100)
        
        # Crear barra de progreso
        bars = 10
        filled_bars = int(percentage / 100 * bars)
        bar = "😍" * filled_bars + "⚫" * (bars - filled_bars)
        
        mensajes = [
            f"🤡 **{target.display_name}** es **{percentage}%** simp!\n{bar}",
            f"💸 **Nivel de Simp** de **{target.display_name}**: **{percentage}%**\n{bar}",
            f"🎭 **Medidor Simp**: **{target.display_name}** - **{percentage}%**\n{bar}"
        ]
        
        if percentage > 80:
            mensajes.append(f"🚨 **ALERTA SIMP**! **{target.display_name}** es **{percentage}%** simp! Cuidado!\n{bar}")
        
        await interaction.response.send_message(random.choice(mensajes))
    
    @app_commands.command(name='ship', description='Ship de dos usuarios')
    @app_commands.describe(usuario1="Primer usuario", usuario2="Segundo usuario")
    async def ship_command(self, interaction: discord.Interaction, usuario1: discord.Member, usuario2: discord.Member):
        """Ship de usuarios"""
        if usuario1 == usuario2:
            await interaction.response.send_message("❌ No puedes shipear a alguien consigo mismo... eso sería narcisismo 😅", ephemeral=True)
            return
        
        percentage = random.randint(0, 100)
        ship_name = (usuario1.display_name[:3] + usuario2.display_name[-3:]).lower()
        
        # Crear barra de progreso
        bars = 10
        filled_bars = int(percentage / 100 * bars)
        bar = "❤️" * filled_bars + "⚫" * (bars - filled_bars)
        
        mensajes = [
            f"💞 **{usuario1.display_name}** + **{usuario2.display_name}** = **{ship_name}**\n**Compatibilidad:** {percentage}%\n{bar}",
            f"👩‍❤️‍👨 **Ship**: **{usuario1.display_name}** 💕 **{usuario2.display_name}**\n**Amor:** {percentage}%\n{bar}",
            f"💑 **{usuario1.display_name}** y **{usuario2.display_name}** tienen {percentage}% de química!\n{bar}"
        ]
        
        if percentage > 80:
            mensajes.append(f"💘 **MATCH PERFECTO!** **{usuario1.display_name}** + **{usuario2.display_name}** = **{ship_name}**\n**Amor:** {percentage}% 💖\n{bar}")
        elif percentage < 20:
            mensajes.append(f"💔 **No hay química...** **{usuario1.display_name}** y **{usuario2.display_name}** tienen solo {percentage}% de compatibilidad\n{bar}")
        
        await interaction.response.send_message(random.choice(mensajes))
    
    # PANEL DE DIVERSIÓN
    
    @app_commands.command(name='diversion', description='Panel de comandos de diversión disponibles')
    async def diversion_panel(self, interaction: discord.Interaction):
        """Panel con todos los comandos de diversión disponibles"""
        embed = discord.Embed(
            title="🎉 Panel de Diversión - Comandos /",
            description="**Todos estos comandos usan el sistema slash `/`**\n\n"
                      "**🎭 Comandos de Emociones:**\n"
                      "`/soy` - Te dice algo bonito\n"
                      "`/abrazo [@usuario]` - Dar un abrazo\n"
                      "`/beso [@usuario]` - Dar un beso\n\n"
                      "**🎯 Comandos de Interacción:**\n"
                      "`/decide [opciones]` - Elige por ti\n"
                      "`/bola8 [pregunta]` - Bola mágica 8\n"
                      "`/dado [caras]` - Tirar un dado\n"
                      "`/ship [@user1] [@user2]` - Shipear usuarios\n\n"
                      "**😄 Comandos de Medidores:**\n"
                      "`/gay [@usuario]` - Medidor gay\n"
                      "`/simp [@usuario]` - Medidor simp\n\n"
                      "**🎰 Comandos de Casino:**\n"
                      "`/casino` - Juegos de casino\n"
                      "`/balance` - Ver tu dinero\n"
                      "`/daily` - Reclamar daily\n"
                      "`/work` - Trabajar por dinero\n\n"
                      "**🌐 Comandos de Configuración:**\n"
                      "`/idioma [es/en]` - Cambiar idioma",
            color=config.BOT_COLORS["primary"]
        )
        
        embed.set_footer(text="Usa / y escribe el nombre del comando para ver las opciones")
        await interaction.response.send_message(embed=embed)
    
    # COMANDOS DE UTILIDADES (CON NOMBRES ÚNICOS)
    
    @app_commands.command(name='servidor', description='Información del servidor')
    async def server_info(self, interaction: discord.Interaction):
        """Información del servidor"""
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"ℹ️ Información de {guild.name}",
            color=config.BOT_COLORS["primary"],
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="👥 Miembros", value=guild.member_count, inline=True)
        embed.add_field(name="📅 Creado", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="👑 Dueño", value=guild.owner.mention, inline=True)
        embed.add_field(name="📊 Canales", value=len(guild.channels), inline=True)
        embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="🚀 Boost", value=guild.premium_subscription_count, inline=True)
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name='usuario', description='Información de un usuario')
    @app_commands.describe(miembro="Usuario del que quieres información")
    async def user_info(self, interaction: discord.Interaction, miembro: discord.Member = None):
        """Información de un usuario"""
        if miembro is None:
            miembro = interaction.user
        
        embed = discord.Embed(
            title=f"👤 Información de {miembro.display_name}",
            color=miembro.color if miembro.color != discord.Color.default() else config.BOT_COLORS["primary"],
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="🆔 ID", value=miembro.id, inline=True)
        embed.add_field(name="📅 Cuenta creada", value=miembro.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="📥 Se unió", value=miembro.joined_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="🎭 Rol más alto", value=miembro.top_role.mention, inline=True)
        embed.add_field(name="🤖 Es bot", value="Sí" if miembro.bot else "No", inline=True)
        
        if miembro.avatar:
            embed.set_thumbnail(url=miembro.avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name='infobot', description='Información del bot')
    async def info_bot(self, interaction: discord.Interaction):  # CAMBIADO: de bot_info a info_bot
        """Información del bot"""
        embed = discord.Embed(
            title="🤖 Información del Bot",
            description="Bot multifunción con sistema de tickets, moderación, seguridad, casino y diversión",
            color=config.BOT_COLORS["primary"],
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="📊 Servidores", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="⚡ Latencia", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="🕒 Tiempo activo", value=self.get_uptime(), inline=True)
        embed.add_field(name="🔧 Funciones", value="Tickets • Moderación • Seguridad • Casino • Utilidades • Diversión", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name='latencia', description='Ver la latencia del bot')
    async def latencia(self, interaction: discord.Interaction):
        """Ver la latencia del bot"""
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latencia:** {round(self.bot.latency * 1000)}ms",
            color=config.BOT_COLORS["success"]
        )
        await interaction.response.send_message(embed=embed)
    
    def get_uptime(self):
        delta = discord.utils.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

async def setup(bot):
    await bot.add_cog(Utilities(bot))