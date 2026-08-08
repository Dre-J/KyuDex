import discord
from discord.ext import commands

import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp
import discord

# --- Color Constants ---
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
BLACK_50 = (0, 0, 0, 128)
GRAY = (50, 50, 50, 255)
LIGHT_GRAY = (70, 70, 70, 255)
GREEN = (46, 204, 113, 255)
LIGHT_GREEN = (150, 255, 150, 255)
PALE_GREEN = (229, 255, 224, 255)
YELLOW = (241, 196, 15, 255)
LIGHT_YELLOW = (255, 255, 150, 255)
RED = (231, 76, 60, 255)
LIGHT_RED = (255, 150, 150, 255)
PALE_RED = (255, 229, 224, 255)

import discord

class BattlefieldInfoView(discord.ui.View):
    def __init__(self, weather, terrain, p_status, n_status, p_hazards, n_hazards, p_stats, n_stats):
        super().__init__(timeout=None) 
        self.weather = weather.title() if weather and weather != 'none' else "Clear"
        self.terrain = terrain.title() if terrain and terrain != 'none' else "Normal Ground"
        self.p_status = p_status
        self.n_status = n_status
        self.p_hazards = p_hazards
        self.n_hazards = n_hazards
        self.p_stats = p_stats
        self.n_stats = n_stats

    def format_dict_data(self, data_dict, is_stats=False):
        """A single helper to format both hazards and stat boosts nicely."""
        if not data_dict:
            return "None"
        
        lines = []
        for key, value in data_dict.items():
            name = key.upper() if is_stats else key.title().replace('-', ' ')
            
            if is_stats and value != 0:
                sign = "+" if value > 0 else ""
                lines.append(f"• **{name}**: {sign}{value}")
            elif not is_stats:
                if type(value) == int and value > 1:
                    lines.append(f"• **{name}**: {value} Layers")
                elif value:
                    lines.append(f"• **{name}**")
                    
        return "\n".join(lines) if lines else "None"

    def format_status(self, status):
        """Extracts the status name whether it's passed as a string or a dict."""
        if not status:
            return "Healthy"
        if isinstance(status, dict):
            return status.get('name', status.get('status', 'Healthy')).title()
        return str(status).title()

    @discord.ui.button(label="Battle Details", style=discord.ButtonStyle.secondary, emoji="📊")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Current Battlefield Conditions", color=0x3498db)
        
        # Row 1: Environment
        embed.add_field(name="🌤️ Weather", value=self.weather, inline=True)
        embed.add_field(name="🌱 Terrain", value=self.terrain, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=False) 
        
        # Row 2: Status Effects
        p_stat_str = self.format_status(self.p_status)
        n_stat_str = self.format_status(self.n_status)
        embed.add_field(name="Your Status", value=f"**{p_stat_str}**", inline=True)
        embed.add_field(name="Enemy Status", value=f"**{n_stat_str}**", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=False) 

        # Row 3: Stat Changes
        embed.add_field(name="Your Stat Changes", value=self.format_dict_data(self.p_stats, True), inline=True)
        embed.add_field(name="Enemy Stat Changes", value=self.format_dict_data(self.n_stats, True), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=False) 

        # Row 4: Hazards
        embed.add_field(name="Hazards on Your Side", value=self.format_dict_data(self.p_hazards), inline=True)
        embed.add_field(name="Hazards on Enemy Side", value=self.format_dict_data(self.n_hazards), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

class BattleSceneGenerator:
    # --- UI Drawing Helpers ---
    @staticmethod
    def get_status_info(status_input):
        """Safely parses a string or dict and returns the proper color and 3-letter abbreviation."""
        if not status_input: return GRAY, ""
            
        # Extract the string, handling simple strings or dictionaries like {'name': 'burn'}
        if isinstance(status_input, dict):
            s = status_input.get('name', status_input.get('status', ''))
        else:
            s = str(status_input)
            
        s = s.upper()
        
        # Robust Mapping: Full words to colors and standard abbreviations
        if s in ["BRN", "BURN"]: return (231, 76, 60, 255), "BRN"
        if s in ["PSN", "POISON"]: return (155, 89, 182, 255), "PSN"
        if s in ["TOX", "BAD POISON", "TOXIC"]: return (142, 68, 173, 255), "TOX"
        if s in ["PAR", "PARALYZE", "PARALYSIS"]: return (243, 156, 18, 255), "PAR"
        if s in ["SLP", "SLEEP"]: return (149, 165, 166, 255), "SLP"
        if s in ["FRZ", "FREEZE", "FROZEN"]: return (135, 206, 235, 255), "FRZ"
        
        return GRAY, s[:3] # Fallback for unknown statuses

    @staticmethod
    def _draw_rain_elements(draw, count=80):
        """Draws small, angled blue streaks to simulate rain."""
        for _ in range(count):
            # Random starting position
            x = random.randint(0, 600)
            y = random.randint(0, 300)
            
            # Use random slant and varying opacity for depth
            length = random.randint(5, 12)
            alpha = random.randint(80,100)
            draw.line([(x, y), (x + 2, y + length)], fill=(120, 200, 255, alpha), width=1)

    @staticmethod
    def _draw_hail_elements(draw, count=60):
        """Draws various sized white dots to simulate snowflakes/hail."""
        for _ in range(count):
            # Procedural circles of varying sizes and opacity
            x = random.randint(0, 600)
            y = random.randint(0, 300)
            radius = random.randint(1, 3)
            alpha = random.randint(100, 200)
            draw.ellipse([(x, y), (x + radius*2, y + radius*2)], fill=(255, 255, 255, alpha))

    @staticmethod
    def _draw_sandstorm_elements(draw, total_points=200):
        """Draws thicker, darker, clustered dust motes to simulate deep sand."""
        clusters = 6 # Increased clusters for better canvas spread
        points_per_cluster = total_points // clusters
        
        for _ in range(clusters):
            # Cluster base point
            base_x = random.randint(50, 550)
            base_y = random.randint(50, 250)
            
            for _ in range(points_per_cluster):
                # Spread dots further around the base point
                x = base_x + random.randint(-25, 25)
                y = base_y + random.randint(-25, 25)
                
                # Canvas bounds check
                x = max(0, min(600, x))
                y = max(0, min(300, y))
                
                # Much higher opacity for visibility
                alpha = random.randint(150, 255) 
                
                # Randomize size to be 1 or 2 pixels wide instead of a microscopic single point
                size = random.randint(1, 2)
                
                # Darker dirt brown color
                draw.ellipse([(x, y), (x + size, y + size)], fill=(101, 67, 33, alpha))
    
    @staticmethod
    def draw_b2w2_plate(draw, x, y, width, height, is_player):
        slant = 20
        fill_color = (35, 35, 35, 230)      
        outline_color = (120, 120, 120, 255) 
        
        if is_player:
            poly = [(x, y + height), (x + slant, y), (x + width, y), (x + width - slant, y + height)]
        else:
            poly = [(x, y), (x + width - slant, y), (x + width, y + height), (x + slant, y + height)]
            
        draw.polygon(poly, fill=fill_color, outline=outline_color, width=2)

    @staticmethod
    def draw_rounded_rectangle(draw, xy, radius, fill=None, outline=None, width=1):
        x1, y1, x2, y2 = xy
        draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill, outline=outline, width=width)
        draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill, outline=outline, width=width)
        draw.pieslice((x1, y1, x1 + 2*radius, y1 + 2*radius), 180, 270, fill=fill, outline=outline)
        draw.pieslice((x2 - 2*radius, y1, x2, y1 + 2*radius), 270, 360, fill=fill, outline=outline)
        draw.pieslice((x1, y2 - 2*radius, x1 + 2*radius, y2), 90, 180, fill=fill, outline=outline)
        draw.pieslice((x2 - 2*radius, y2 - 2*radius, x2, y2), 0, 90, fill=fill, outline=outline)

    @staticmethod
    def draw_hp_bar(draw, x, y, width, height, ratio):
        slant = 10 
        fill_width = width * ratio
        fill_right = x + fill_width

        base = [(x + slant, y), (x + width, y), (x + width - slant, y + height), (x, y + height)]
        
        hp_color = GREEN if ratio > 0.5 else YELLOW if ratio > 0.2 else RED
        light_color = LIGHT_GREEN if ratio > 0.5 else LIGHT_YELLOW if ratio > 0.2 else LIGHT_RED

        draw.polygon(base, fill=GRAY)
        
        if ratio > 0:
            fill = [
                (x + slant, y), (min(fill_right, x + width), y),
                (max(x, min(fill_right - slant, x + width - slant)), y + height), (x, y + height)
            ]
            draw.polygon(fill, fill=hp_color)
            
            highlight = [
                (x + (slant // 2) + 5, y + 2),
                (min(fill_right - 2, x + width - 10), y + 2),
                (max(x, min(fill_right - (slant // 2) - 10, x + width - (slant // 2) - 10)), y + height // 2),
                (x + 5, y + height // 2)
            ]
            draw.polygon(highlight, fill=light_color)
            
        draw.polygon(base, outline=BLACK, width=2)

    @staticmethod
    def get_biome_background(biome_name):
        """Fetches a background image based on the biome name, with a safe fallback."""
        
        # Map your biome names to the actual file paths
        biomes = {
            'forest': 'assets/bg_forest.png',
            'cave': 'assets/bg_cave.png',
            'water': 'assets/bg_water.png',
            'city': 'assets/city.png',
            'default': 'assets/bg_field.png'
        }

        # Grab the path, defaulting to 'default' if the biome isn't recognized
        file_path = biomes.get(biome_name.lower(), biomes['default'])

        try:
            # Open the image, ensure it supports transparency, and force it to our canvas size
            bg_image = Image.open(file_path).convert("RGBA")
            return bg_image.resize((600, 300), Image.Resampling.LANCZOS)
            
        except FileNotFoundError:
            # The Safe Fallback: If you forget to upload the image, it won't crash the bot!
            print(f"⚠️ Warning: {file_path} not found. Falling back to procedural grass.")
            
            fallback = Image.new('RGBA', (600, 300), (135, 206, 235, 255)) 
            fallback_draw = ImageDraw.Draw(fallback)
            fallback_draw.rectangle([0, 150, 600, 300], fill=(120, 200, 80, 255))
            return fallback

    async def generate_battle_scene(self, player_id, npc_id, p_hp, p_max_hp, n_hp, n_max_hp, 
                                        player_shiny=False, npc_shiny=False, weather='none', biome='default'):
        
        base_url = "https://raw.githubusercontent.com/Dre-J/pokebotsprites/refs/heads/master/sprites/pokemon/other/official-artwork"
        p_url = f"{base_url}/shiny/{player_id}.png" if player_shiny else f"{base_url}/{player_id}.png"
        n_url = f"{base_url}/shiny/{npc_id}.png" if npc_shiny else f"{base_url}/{npc_id}.png"

        async with aiohttp.ClientSession() as session:
            async with session.get(p_url) as resp1: p_data = await resp1.read() if resp1.status == 200 else None
            async with session.get(n_url) as resp2: n_data = await resp2.read() if resp2.status == 200 else None

        fallback_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDAT\x08\x99c\xf8\x0f\x04\x00\x09\xfb\x03\xfd\xe3U\xf2\x9c\x00\x00\x00\x00IEND\xaeB`\x82'
        
        p_img = Image.open(BytesIO(p_data if p_data else fallback_bytes)).convert("RGBA")
        n_img = Image.open(BytesIO(n_data if n_data else fallback_bytes)).convert("RGBA")

        p_img = ImageOps.mirror(p_img).resize((180, 180), Image.Resampling.LANCZOS)
        n_img = n_img.resize((180, 180), Image.Resampling.LANCZOS)

        # Procedural base background
        bg = self.get_biome_background(biome)

        # Paste Sprites
        bg.paste(n_img, (400, 60), n_img)   
        bg.paste(p_img, (70, 80), p_img)  

        # ==========================================
        # ATMOSPHERIC WEATHER OVERLAY
        # ==========================================
        environment_layer = Image.new('RGBA', bg.size, (0, 0, 0, 0))
        element_draw = ImageDraw.Draw(environment_layer)
        has_elements = False

        if weather and weather.lower() != 'none':
            weather_colors = {
                'rain': (0, 70, 255, 20),      
                'sun': (255, 170, 0, 50),      
                'sand': (210, 180, 140, 80),   
                'hail': (200, 240, 255, 70)    
            }
            tint = weather_colors.get(weather.lower(), (255, 255, 255, 0)) 
            
            if tint[3] > 0:
                tint_layer = Image.new('RGBA', bg.size, tint)
                bg = Image.alpha_composite(bg, tint_layer)

            w = weather.lower()
            if w == 'rain':
                self._draw_rain_elements(element_draw, count=80)
                has_elements = True
            elif w == 'hail':
                self._draw_hail_elements(element_draw, count=50)
                has_elements = True
            elif w == 'sand':
                self._draw_sandstorm_elements(element_draw, total_points=200)
                has_elements = True

        if has_elements:
            bg = Image.alpha_composite(bg, environment_layer)

        # --- Draw HUD Plates ---
        overlay = Image.new('RGBA', bg.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Player Plate (Bottom Left) - Width reduced from 260 to 200
        self.draw_b2w2_plate(overlay_draw, 50, 250, 200, 40, is_player=True)
        # NPC Plate (Top Right) - Width reduced from 250 to 190. Shifted right to x=350.
        self.draw_b2w2_plate(overlay_draw, 350, 25, 190, 35, is_player=False)

        bg = Image.alpha_composite(bg, overlay)
        draw = ImageDraw.Draw(bg)
        font = ImageFont.load_default()

        # ==========================================
        # NPC HUD
        # ==========================================
        draw.text((350, 10), "Enemy Pkmn", fill=BLACK, font=font)
        draw.text((500, 10), "Lv. 50", fill=BLACK, font=font) 
        
        # HP Bar width reduced to 140
        self.draw_hp_bar(draw, 365, 33, 140, 10, max(0.0, min(1.0, n_hp / max(1, n_max_hp))))
        draw.text((450, 48), f"{n_hp} / {n_max_hp}", fill=WHITE, font=font)

        # ==========================================
        # PLAYER HUD
        # ==========================================
        draw.text((60, 240), "Your Pkmn", fill=BLACK, font=font)
        draw.text((210, 240), "Lv. 50", fill=BLACK, font=font)
        
        # HP Bar width reduced to 140
        self.draw_hp_bar(draw, 80, 265, 140, 10, max(0.0, min(1.0, p_hp / max(1, p_max_hp))))
        draw.text((165, 277), f"{p_hp} / {p_max_hp}", fill=WHITE, font=font)

        # --- Export ---
        buffer = BytesIO()
        bg.save(buffer, format="PNG")
        buffer.seek(0)
        
        return discord.File(fp=buffer, filename=f"battle_{random.randint(10000, 99999)}.png")
    
class BattleTesting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = BattleSceneGenerator() # Initialize your visual engine

    @commands.command(name="testhud")
    async def test_battle_ui(self, ctx):
        loading_msg = await ctx.send("⚙️ Compiling battle UI data...")

        # Your mock data
        player_id = 445  # Garchomp
        npc_id = 248     # Tyranitar
        p_hp, p_max_hp = 1, 240
        n_hp, n_max_hp = 40, 265
        p_status = "burn"
        n_status = "poison"
        p_hazards = {'stealth-rock': True, 'spikes': 2}
        n_hazards = {'toxic-spikes': 1, 'sticky-web': True}
        p_stats = {'atk': 2, 'spe': 1}
        n_stats = {'def': 1, 'spd': -1}
        weather = 'rain'
        terrain = 'misty'
        biome = 'city' # The terrain won't render visually anymore, but the button will know it's there!

        try:
            # 1. Generate the image (Assuming you've stripped out the _draw_terrain_elements logic)
            battle_image = await self.engine.generate_battle_scene(
                player_id=player_id, npc_id=npc_id,
                p_hp=p_hp, p_max_hp=p_max_hp, n_hp=n_hp, n_max_hp=n_max_hp,
                weather=weather, biome='city'
            )
            
            # 2. Initialize the View with the environment data
            view = BattlefieldInfoView(p_status=p_status, n_status=n_status,p_stats=p_stats, n_stats=n_stats, weather=weather, terrain=terrain, p_hazards=p_hazards, n_hazards=n_hazards)
            
            # 3. Send the image AND the view button
            await ctx.send(file=battle_image, view=view)
            await loading_msg.delete()
            
        except Exception as e:
            await loading_msg.edit(content=f"❌ **Visual Engine Error:** {e}")
# Don't forget the setup function required by discord.py cogs!
async def setup(bot):
    await bot.add_cog(BattleTesting(bot))