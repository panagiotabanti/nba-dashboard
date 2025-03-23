import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import (
    playercareerstats,
    scoreboardv2,
    leaguestandings,
    leaguedashteamstats
)
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="NBA Dashboard", layout="wide")

# --- SIDEBAR ---
st.sidebar.image("https://cdn.nba.com/logos/nba/nba-logo.svg", width=100)
st.sidebar.title(" NBA Dashboard")
st.sidebar.markdown("Compare players, view team stats, track standings, and follow the league.")

theme = st.sidebar.radio("Theme", ["Light", "Dark"], index=0)
season = st.sidebar.selectbox("Select Season:", ["2023-24", "2022-23", "2021-22", "2020-21"])

# --- THEME STYLING ---
if theme == "Light":
    background_color = "#f0f2f6"
    text_color = "#000000"
    cmap = "Blues"
    plt.style.use("default")
else:
    background_color = "#1e1e1e"
    text_color = "#ffffff"
    cmap = "Greys"
    plt.style.use("dark_background")

st.markdown(f"""
    <style>
    html, body {{
        background-color: {background_color};
        color: {text_color};
    }}
    [class*="block-container"] {{
        background-color: {background_color};
        color: {text_color};
    }}
    </style>
    """, unsafe_allow_html=True)

# --- TITLE ---
st.title(" NBA Player Comparison Dashboard")
st.markdown(f"Season: **{season}** | Theme: **{theme}**")
st.markdown("---")

# --- LIVE NBA GAMES ---
st.subheader("📺 Live NBA Games Today")
try:
    today = datetime.today().strftime('%m/%d/%Y')
    live_games = scoreboardv2.ScoreboardV2(game_date=today).get_normalized_dict()
    games = live_games['GameHeader']
    line_scores = live_games['LineScore']

    if not games:
        st.info("No NBA games scheduled for today.")
    else:
        for game in games:
            status = game['GAME_STATUS_TEXT']
            scores = [s for s in line_scores if s['GAME_ID'] == game['GAME_ID']]
            if len(scores) == 2:
                t1 = scores[0]
                t2 = scores[1]
                st.markdown(f"**{t1['TEAM_ABBREVIATION']} {t1['PTS']} - {t2['PTS']} {t2['TEAM_ABBREVIATION']}** — *{status}*")
    st.caption(f"Checked date: {today}")
except:
    st.warning("Live games not available.")

st.markdown("---")

# --- TEAM "STANDINGS" USING STATS ---
st.subheader("📊 NBA Team Rankings (Based on Win %)")
try:
    team_stats = leaguedashteamstats.LeagueDashTeamStats(season=season).get_data_frames()[0]

    # Add Win % as percentage
    team_stats['Win %'] = (team_stats['W'] / (team_stats['W'] + team_stats['L'])).round(3) * 100

    # Filter by conference if selected
    conference_filter = st.radio("Select Conference:", ["All", "East", "West"], horizontal=True)
    if conference_filter != "All":
        team_stats = team_stats[team_stats['CONF_RANK'].notna()]  # Ensure column exists
        team_stats = team_stats[team_stats['CONFERENCE'] == conference_filter]

    display = team_stats[['TEAM_NAME', 'W', 'L', 'Win %']]
    display = display.rename(columns={
    'TEAM_NAME': 'Team',
    'W': 'Wins',
    'L': 'Losses'
    }).sort_values(by='Win %', ascending=False)


    st.dataframe(display.reset_index(drop=True), use_container_width=True)
except Exception as e:
    st.error("Could not fetch team rankings.")


# --- TOP 5 TEAMS BY PPG ---
st.subheader("Top 5 Teams by Points Per Game")
try:
    team_stats = leaguedashteamstats.LeagueDashTeamStats(season=season).get_data_frames()[0]
    top5 = team_stats[['TEAM_NAME', 'PTS']].sort_values(by='PTS', ascending=False).head(5)
    fig, ax = plt.subplots()
    ax.bar(top5['TEAM_NAME'], top5['PTS'], color='orange')
    ax.set_ylabel("Points Per Game")
    ax.set_title(f"Top 5 Teams (Season {season})")
    st.pyplot(fig)
except:
    st.warning("Could not load top scoring teams.")

# --- TEAM STATS DROPDOWN ---
st.subheader(" View Team Stats")
try:
    team_stats = leaguedashteamstats.LeagueDashTeamStats(season=season).get_data_frames()[0]
    selected_team = st.selectbox("Select a team:", sorted(team_stats['TEAM_NAME'].unique()))
    selected_df = team_stats[team_stats['TEAM_NAME'] == selected_team].T
    selected_df.columns = [selected_team]
    st.dataframe(selected_df, use_container_width=True)
except:
    st.warning("Could not load team stats.")

# --- PLAYER COMPARISON ---
st.markdown("---")
st.subheader("👥 Compare Player Stats")

player_dict = players.get_players()
player_names = [p['full_name'] for p in player_dict]

col1, col2 = st.columns(2)
with col1:
    player1_name = st.selectbox("Select Player 1:", player_names, key='p1')
with col2:
    player2_name = st.selectbox("Select Player 2:", player_names, key='p2')

# Playoffs toggle
playoffs = st.checkbox("Include Playoff Stats")

def get_player_stats(name, playoffs=False):
    for p in player_dict:
        if p['full_name'] == name:
            player_id = p['id']
            career = playercareerstats.PlayerCareerStats(player_id=player_id)
            df = career.get_data_frames()[0]
            if playoffs:
                df = df[df['SEASON_ID'].str.contains('P')]
            else:
                df = df[~df['SEASON_ID'].str.contains('P')]
            return df
    return None

def get_averages(df):
    totals = df[['GP', 'PTS', 'AST', 'REB', 'FG_PCT', 'FG3_PCT', 'FT_PCT']].sum()
    games_played = df['GP'].sum()
    if games_played == 0:
        return None
    return {
        'PTS': totals['PTS'] / games_played,
        'AST': totals['AST'] / games_played,
        'REB': totals['REB'] / games_played,
        'FG%': totals['FG_PCT'] / len(df),
        '3P%': totals['FG3_PCT'] / len(df),
        'FT%': totals['FT_PCT'] / len(df)
    }

if player1_name and player2_name:
    df1 = get_player_stats(player1_name, playoffs)
    df2 = get_player_stats(player2_name, playoffs)

    if df1 is not None and df2 is not None:
        avg1 = get_averages(df1)
        avg2 = get_averages(df2)

        if avg1 and avg2:
            st.subheader(" Career Averages")
            stats_df = pd.DataFrame({
                player1_name: avg1,
                player2_name: avg2
            })
            st.dataframe(stats_df.style.format("{:.2f}").background_gradient(axis=1, cmap=cmap))

            st.subheader(" Stat Comparison")
            stat_names = list(avg1.keys())
            values1 = list(avg1.values())
            values2 = list(avg2.values())

            fig, ax = plt.subplots(figsize=(10, 5))
            bar_width = 0.35
            index = range(len(stat_names))

            ax.bar(index, values1, bar_width, label=player1_name)
            ax.bar([i + bar_width for i in index], values2, bar_width, label=player2_name)

            ax.set_xlabel('Stat')
            ax.set_ylabel('Average')
            ax.set_title('Stat Comparison')
            ax.set_xticks([i + bar_width / 2 for i in index])
            ax.set_xticklabels(stat_names)
            ax.legend()

            st.pyplot(fig)
        else:
            st.error("No data to compare.")
    else:
        st.error("Could not retrieve player data.")
