import os
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# カテゴリーIDと管理者ロールID
TICKET_CATEGORY_ID = 1450086411956129894  # チケット用カテゴリー
DONE_CATEGORY_ID = 1450086104182034512    # 対応済み移動先カテゴリー
ADMIN_ROLE_ID = 1313086280141373441       # 管理者ロールID

# --- /ticket-panel ---
class TicketSelect(ui.Select):
    def __init__(self, user: discord.Member):
        options = [
            discord.SelectOption(label="ゲーム", description="ゲーム関連の問い合わせ"),
            discord.SelectOption(label="アカウント", description="アカウント関連の問い合わせ"),
            discord.SelectOption(label="その他", description="その他の問い合わせ"),
        ]
        super().__init__(placeholder="チケットの種類を選択", min_values=1, max_values=1, options=options)
        self.user = user

    async def callback(self, interaction: Interaction):
        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("カテゴリーが見つかりません。", ephemeral=True)
            return

        # チャンネル作成
        ch_name = f"{self.user.name}-ticket-{self.values[0]}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_id in [ADMIN_ROLE_ID]:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await category.create_text_channel(ch_name, overwrites=overwrites)

        # チャンネルに埋め込みとボタン送信
        embed = discord.Embed(
            title=f"{self.user.name}のTicket | {self.values[0]}",
            description=f"管理者の対応をお待ちください。\n※対応が遅れる場合があります。",
            color=0x00ff00
        )
        view = TicketView(self.user)
        await ticket_channel.send(content=f"{self.user.mention} 要件を言い、お待ちください！", embed=embed, view=view)
        await interaction.response.send_message(f"{ticket_channel.mention} にチケットを作成しました。", ephemeral=True)


class TicketView(ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=None)
        self.user = user
        self.add_item(TicketDeleteButton())
        self.add_item(TicketCloseButton(user))


class TicketDeleteButton(ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="チケットを削除")

    async def callback(self, interaction: Interaction):
        await interaction.channel.delete()


class TicketCloseButton(ui.Button):
    def __init__(self, user: discord.Member):
        super().__init__(style=discord.ButtonStyle.secondary, label="対応済み / クローズ")
        self.user = user

    async def callback(self, interaction: Interaction):
        # 発言権限剥奪
        await interaction.channel.set_permissions(self.user, send_messages=False)
        # DONEカテゴリーに移動
        done_category = interaction.guild.get_channel(DONE_CATEGORY_ID)
        if done_category:
            await interaction.channel.edit(category=done_category)
        await interaction.response.send_message("チケットは対応済みとしてクローズされました。", ephemeral=True)


class TicketPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="チケットを作成", style=discord.ButtonStyle.secondary, custom_id="create_ticket"))

    @ui.button(label="チケットを作成", style=discord.ButtonStyle.secondary, custom_id="create_ticket")
    async def create_ticket(self, interaction: Interaction, button: ui.Button):
        # ユーザーにセレクトメニュー表示
        await interaction.response.send_message("チケットの種類を選択してください:", view=TicketSelectView(interaction.user), ephemeral=True)


class TicketSelectView(ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=180)
        self.add_item(TicketSelect(user))


@bot.tree.command(name="ticket-panel", description="チケットパネルを送信")
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title=None,
        description="## __Ticket Panel__\n> 購入：お問い合わせ\n> リンク送信禁止\n> 迷惑行為禁止",
        color=0x808080
    )
    await interaction.response.send_message(embed=embed, view=TicketPanel(), ephemeral=False)

@bot.event
async def on_ready():
    # 全ギルドにスラッシュコマンドを同期
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    print(f"Logged in as {bot.user}")

# 起動
keep_alive()
bot.run(TOKEN)
