import pandas as pd
from sa_constants import saps_ages, sexes, trimmed_employment_status, trimmed_education, saps_citizenships

folder = "./CSVs/0061-00 LFS_Q11998-Q32023/0061-00 LFS/0061-00_Data/CSV/"
file = "0061-24_lfs_2023.csv"

micro_df = pd.read_csv(folder + file)
# micro_df = micro_df[micro_df["refperiod"] == "2023Q3"]

micro_df = micro_df[micro_df['CITIZENSHIP_SUMMARY'].notna()]

micro_df["MY_AGE"] = micro_df.apply(lambda row: saps_ages[row["AGECLASS"]], axis=1)
micro_df["T1_1"] = micro_df.apply(lambda row: saps_ages[row["AGECLASS"]] + sexes[row["SEX"]], axis=1)
micro_df["MY_SEX"] = micro_df.apply(lambda row: sexes[row["SEX"]], axis=1)
micro_df["T2_1"] = micro_df.apply(lambda row: saps_citizenships[row["CITIZENSHIP_SUMMARY"]], axis=1)
micro_df["T8_1"] = micro_df.apply(trimmed_employment_status, axis=1)
micro_df["T10_"] = micro_df.apply(trimmed_education, axis=1)
# micro_df = micro_df[["MY_SEX", "MY_AGE", "T2_1", "T8_1", "T10_"]]
micro_df = micro_df[["MY_SEX", "MY_AGE", "T2_1", "T8_1", "T10_", "refperiod"]]
micro_df = micro_df[~micro_df.MY_AGE.isin(["T1_1AGE0_4", "T1_1AGE5_9", "T1_1AGE10_14"])]
micro_df = micro_df[micro_df.T8_1 != "S"]

# columns_of_interest = ["T8_1", "MY_AGE", "MY_SEX", "T2_1", "T10_"]
columns_of_interest = ["MY_AGE", "MY_SEX", "T2_1", "T10_"] #,  ""]

for group, groups_rows in micro_df.groupby(columns_of_interest):
    print(group)
    print(groups_rows.value_counts("refperiod"))

# crosstab = pd.crosstab(micro_df[columns_of_interest[0]], [micro_df[c] for c in columns_of_interest[1:]], dropna=True, normalize="columns")
# crosstab = crosstab.to_dict()
# print(crosstab)
