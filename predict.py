import numpy as np
import pandas as pd
from scipy.stats import poisson
import statsmodels.api as sm
import statsmodels.formula.api as smf
import bot
import random


def simulate_match(model, home, away, max_goals=10):
    home_goals_avg = model.predict(pd.DataFrame(data={"scoring": home, "conceding": away, "home_status": 1},
                                                index=[0]))
    away_goals_avg = model.predict(pd.DataFrame(data={"scoring": away, "conceding": home, "home_status": 0},
                                                index=[0]))
    predictions = [[poisson.pmf(i, team_avg) for i in range(0, max_goals + 1)]
                   for team_avg in [home_goals_avg, away_goals_avg]]
    return np.outer(np.array(predictions[0]), np.array(predictions[1]))


def fill_test_df(test_df):
    home_teams = []
    away_teams = []
    pred_home = []
    pred_away = []

    for n in range(0, len(test_df["HomeTeam"])):
        sim = simulate_match(poisson_model, test_df["HomeTeam"].loc[n], test_df["AwayTeam"].loc[n],
                             max_goals=10)
        unraveled = np.unravel_index(sim.argmax(), sim.shape)

        home_teams.append(test_df["HomeTeam"].loc[n])
        away_teams.append(test_df["AwayTeam"].loc[n])
        pred_home.append(unraveled[0])
        pred_away.append(unraveled[1])

    test_df = pd.DataFrame({"HomeTeam": home_teams, "AwayTeam": away_teams,
                            "HomePredicted": pred_home, "AwayPredicted": pred_away})
    return test_df


def transform_df(test_df):
    test_df["HomeScore"] = test_df["HomePredicted"].round(0).astype(int)
    test_df["AwayScore"] = test_df["AwayPredicted"].round(0).astype(int)
    test_df.loc[(test_df["HomeScore"] > test_df["AwayScore"]), "1x2_Pred"] = "1"
    test_df.loc[(test_df["HomeScore"] == test_df["AwayScore"]), "1x2_Pred"] = "X"
    test_df.loc[(test_df["HomeScore"] < test_df["AwayScore"]), "1x2_Pred"] = "2"
    return test_df


def to_string(predicted_matches):
    final_string = "Kupon oluşturuluyor...\n"
    pred_list = []
    for i in range(13):
        match = str(predicted_matches["HomeTeam"][i]) + " - " + str(predicted_matches["AwayTeam"][i]) \
                + " MS " + predicted_matches["1x2_Pred"][i] + "\n"
        pred_list.append(match)
    choice_list = random.sample(pred_list, k=4)
    for string in choice_list:
        final_string += string
    final_string += "Tekrar kupon almak için 15 saniye bekleyin, ardından /kupon komutunu tekrar kullanın."
    return final_string


def main():
    on = True
    while on:
        initial_length = len(bot.get_updates()["result"])
        text = to_string(predicted_transformed)
        if len(bot.get_updates()["result"]) > initial_length:
            bot.show_bets(bot.get_updates(), text)
            continue
    """user_ids = get_users(get_updates())
        send = int(input("Broadcast (1)"))
        if send == 1:
            text = input("Text: ")
            broadcast(user_ids, text)
        else:
            on = False"""


# Preparing the data
stsl = "https://fixturedownload.com/download/super-lig-2019-TurkeyStandardTime.csv"

df_stsl = pd.read_csv(stsl)
df_stsl = df_stsl.rename(columns={"Home Team": "HomeTeam", "Away Team": "AwayTeam"})
df_stsl = df_stsl.loc[df_stsl["Result"].notnull()]

df_stsl["HomeGoals"] = df_stsl.Result.str[0].astype(int)
df_stsl["AwayGoals"] = df_stsl.Result.str[4].astype(int)
df_stsl = df_stsl[["HomeTeam", "AwayTeam", "HomeGoals", "AwayGoals"]]
# print(df_stsl.head(20))

df_stsl_fix = pd.read_csv(stsl)
df_stsl_fix = df_stsl_fix.rename(columns={"Home Team": "HomeTeam", "Away Team": "AwayTeam"})
df_stsl_fix = df_stsl_fix.loc[df_stsl_fix["Result"].isnull()]
df_stsl_fix = df_stsl_fix.reset_index()[["Round Number", "HomeTeam", "AwayTeam"]]
# print(df_stsl_fix.head(20))


# Rearranging data, to make it suitable for the poisson model
goal_data = pd.concat([df_stsl[["HomeTeam", "AwayTeam", "HomeGoals"]].assign(home_status=1).rename(
    columns={"HomeTeam": "scoring", "AwayTeam": "conceding", "HomeGoals": "goals"}),
    df_stsl[["AwayTeam", "HomeTeam", "AwayGoals"]].assign(home_status=0).rename(
        columns={"AwayTeam": "scoring", "HomeTeam": "conceding", "AwayGoals": "goals"})])

# scoring - shows the capability to score goals
# conceding - shows the "capability" to concede goals
poisson_model = smf.glm(formula="goals ~ home_status + scoring + conceding",
                        data=goal_data, family=sm.families.Poisson()).fit()
# print(poisson_model.summary())

predicted_fixture = fill_test_df(df_stsl_fix)
predicted_transformed = transform_df(predicted_fixture)


if __name__ == "__main__":
    main()
