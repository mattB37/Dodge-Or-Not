import cassiopeia as cass
from cassiopeia.core import Summoner, MatchHistory, Match
from cassiopeia import Queue, Patch
import arrow
import random
import roleml
from collections import defaultdict
from copy import deepcopy
import pandas as pd
import numpy as np
from IPython.display import display
import os

# set riot api key using windows environmental variables
cass.set_riot_api_key(os.environ["RIOT_API_KEY"])
cass.set_default_region("NA")
weeks = 2

# filter the match history to only include previous x weeks


def filter_match_history_week(summoner, weeks):
    begin_time = arrow.now().shift(weeks=-weeks)
    matches = MatchHistory(
        summoner=summoner,
        queues={Queue.ranked_solo_fives},
        begin_time=begin_time,
        end_time=arrow.now(),
    )
    return matches

# sort the match history object to only include up to the last 20 matches


def get_recent_matchID(summoner, matches):
    pulled_match_ids = []
    if len(matches) == 0:
        return "no recent match history"
    elif len(matches) <= 20:
        for match in matches:
            if match.duration.total_seconds() > 900:
                pulled_match_ids.append(match.id)
    else:
        i = 0
        while i < len(matches) and len(pulled_match_ids) < 20:
            if matches[i].duration.total_seconds() > 900:
                pulled_match_ids.append(matches[i].id)
            i = i+1
    return pulled_match_ids


def get_summoner_stats(summoner, matches):
    dict_summoner_stats = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int)))
    for match in matches:
        roleml.add_cass_predicted_roles(match)
        p = match.participants[summoner]
        role = p.predicted_role
        champ = p.champion.name
        game_length = match.duration.total_seconds() / 60
        dict_summoner_stats[role][champ]["total_game_length"] += game_length
        dict_summoner_stats[role][champ]["total_cs/min"] += (
            p.stats.total_minions_killed + p.stats.neutral_minions_killed
        ) / game_length
        dict_summoner_stats[role][champ]["games played"] += 1
        dict_summoner_stats[role][champ]["total_kills"] += p.stats.kills
        dict_summoner_stats[role][champ]["total_assists"] += p.stats.assists
        dict_summoner_stats[role][champ]["total_deaths"] += p.stats.deaths
        dict_summoner_stats[role][champ]["total_cs"] += (
            p.stats.total_minions_killed + p.stats.neutral_minions_killed
        )
        dict_summoner_stats[role][champ]["total_vision score"] += p.stats.vision_score
        if p.stats.win:
            dict_summoner_stats[role][champ]["total_win_count"] += 1
        if "total_win_count" not in dict_summoner_stats[role][champ].keys():
            dict_summoner_stats[role][champ]["total_win_count"] = 0
        team = p.team
        team_kills = 0
        for participant in team.participants:
            team_kills += participant.stats.kills
        dict_summoner_stats[role][champ]["kp(%)"] = int(
            round((p.stats.kills + p.stats.assists) / team_kills, 2) * 100
        )

    stats = deepcopy(dict_summoner_stats)
    for role in stats.keys():
        for champ in stats[role].keys():
            for stat, val in stats[role][champ].items():
                list_stats = [
                    "total_deaths",
                    "total_assists",
                    "total_kills",
                    "total_cs/min",
                    "total_vision score",
                    "total_cs",
                ]
                if stat == "total_win_count":
                    dict_summoner_stats[role][champ]["winrate(%)"] = int(
                        round(val / stats[role][champ]
                              ["games played"], 1) * 100
                    )
                    continue
                elif stat == "total_game_length":
                    dict_summoner_stats[role][champ]["game length(min)"] = round(
                        val / stats[role][champ]["games played"]
                    )
                    del dict_summoner_stats[role][champ][stat]
                    continue
                elif stat in list_stats:
                    dict_summoner_stats[role][champ][stat[6:]] = round(
                        val / stats[role][champ]["games played"]
                    )
                    del dict_summoner_stats[role][champ][stat]
    return dict_summoner_stats

# filter the original string of summoner names


def filter_summoner_names(lobby_names):
    lobby_names = lobby_names.replace(" joined the lobby", ",")
    lobby_names = lobby_names[: len(lobby_names) - 1]
    lobby_names = "".join(lobby_names.splitlines())
    names_list = lobby_names.split(",")
    return names_list

# format color of winrate column in pandas datatable


def color_winrate(val):
    color = "white"
    if val < 50:
        color = "red"
    elif val > 60:
        color = "green"
    return "color: {}".format(color)

# format color of deaths column in pandas datatable


def color_deaths(val):
    color = "white"
    if val > 7:
        color = "red"
    elif val < 4:
        color = "green"
    return "color: {}".format(color)


def main(summoner_names):
    # filter summoner names out
    name_list = filter_summoner_names(summoner_names)

    # Gather information and format storage in dictionary
    df_dict = dict()
    for name in name_list:
        summoner = cass.get_summoner(name=name)
        df_dict[summoner.name] = []
        match_history = filter_match_history_week(summoner, weeks)
        if not match_history:
            df_dict[summoner.name] = "no recent match history"
            continue
        matchIDs = get_recent_matchID(summoner, match_history)
        matches = [Match(id=id).load() for id in matchIDs]
        for match in matches:
            match.timeline.load()
        stats = get_summoner_stats(summoner, matches)

        # Transfer dictionary to a pandas dataframe and add specific columns/rows
        for role in ["top", "mid", "jungle", "bot", "supp"]:
            df = pd.DataFrame.from_dict(stats[role])
            if not df.empty:
                num = df.loc["games played"].sum()
                wc = df.loc["total_win_count"].sum()
                df.insert(
                    len(df.columns),
                    "OVERALL " + role.upper(),
                    np.round(df.sum(axis=1) /
                             len(stats[role].keys())).astype(int),
                )
                df.at["games played", "OVERALL " + role.upper()] = num
                df.at["total_win_count", "OVERALL " + role.upper()] = wc
                df.at["winrate(%)", "OVERALL " + role.upper()
                      ] = round(wc/num, 2)*100
                df_dict[name].append(df.transpose())

    output = defaultdict()
    for name, df_list in df_dict.items():
        # if the user has no recent match history
        if df_list == "no recent match history":
            output[name] = df_list
            continue
        # style/organize data table
        for df in df_list:
            cols = df.columns.to_list()
            cols.insert(0, cols.pop(cols.index("winrate(%)")))
            cols.insert(1, cols.pop(cols.index("games played")))
            cols.insert(2, cols.pop(cols.index("game length(min)")))
            cols.insert(3, cols.pop(cols.index("kp(%)")))
            cols.insert(4, cols.pop(cols.index("kills")))
            cols.insert(5, cols.pop(cols.index("deaths")))
            cols.insert(6, cols.pop(cols.index("assists")))
            cols.insert(7, cols.pop(cols.index("cs/min")))
            df = df[cols]
            df = (
                df.style.applymap(color_winrate, subset=["winrate(%)"])
                .applymap(color_deaths, subset=["deaths"])
            )
            if name in output.keys():
                output[name].append(df)
            else:
                output[name] = [df]
    # display the data table
    for k in output.keys():
        if output[k] == "no recent match history":
            print("Stats for " + str(k))
            print("no recent match history")
        else:
            print("Stats for " + str(k))
            for df in output[k]:
                display(df)


if __name__ == "__main__":
    main("""ßrody joined the lobbyMr Meat69 joined the lobbyStarBw0y joined the lobbyXephfir joined the lobbyPI PI SHARK joined the lobby""")

# for testing purposes
"""ßrody joined the lobby
Mr Meat69 joined the lobby
StarBw0y joined the lobby
Xephfir joined the lobby
PI PI SHARK joined the lobby"""
