from math import isnan

saps_ages = {1: "T1_1AGE0_4",
             2: "T1_1AGE5_9",
             3: "T1_1AGE10_14",
             4: "T1_1AGE15_19",
             5: "T1_1AGE20_24",
             6: "T1_1AGE25_29",
             7: "T1_1AGE30_34",
             8: "T1_1AGE35_39",
             9: "T1_1AGE40_44",
             10: "T1_1AGE45_49",
             11: "T1_1AGE50_54",
             12: "T1_1AGE55_59",
             13: "T1_1AGE60_64",
             14: "T1_1AGE65_69",
             15: "T1_1AGE70_74",
             16: "T1_1AGE75_79",
             17: "T1_1AGE80_84",
             18: "T1_1AGEGE_85"}

sexes = {1: "M", 2: "F"}

saps_citizenships = {1: "T2_1IEC",
                     2: "T2_1UKC",
                     3: "T2_1EUC",
                     4: "T2_1EUC",
                     5: "T2_1RWC",
                     6: "T2_1RWC"}


saps_levels_of_education = {# No Formal Education
    0: "T10_4_NF",

    # Primary Education
    11: "T10_4_P",
    100: "T10_4_P",

    # Lower Secondary
    21: "T10_4_LS",
    200: "T10_4_LS",

    # Upper Secondary
    22: "T10_4_US",
    30: "T10_4_US",
    32: "T10_4_US",
    300: "T10_4_US",
    303: "T10_4_US",
    304: "T10_4_US",
    343: "T10_4_US",
    344: "T10_4_US",
    399: "T10_4_US",

    # Need to combine T10_4_TV and T10_4_ACCA into T10_4_PLC
    # (Post Leaving Cert)
    42: "T10_4_PLC",
    400: "T10_4_PLC",
    450: "T10_4_PLC",

    # Higher Certificate
    51: "T10_4_HC",
    500: "T10_4_HC",
    540: "T10_4_HC",
    550: "T10_4_HC",
    590: "T10_4_HC",
    52: "T10_4_HC",

    # Need to combine T10_4_ODND and T10_4_HDPQ into T10_4_DGR
    # (degree)
    60: "T10_4_DGR",
    600: "T10_4_DGR",

    # Postgraduate Degree
    700: "T10_4_PD",

    # Doctorate
    800: "T10_4_D",

    # Child
    999: ""
}

saps_employment_statuses = {
    # At Work
    1: "T8_1_W",

    # Need to combine T8_1_LFFJ, T8_1_STU and T8_1_LTU into T8_1_UNE
    2: "T8_1_UNE",

    # Retired
    3: "T8_1_R",

    # Unable to work
    4: "T8_1_UTWSD",

    # Student
    5: "T8_1_S",

    # Home duties
    6: "T8_1_LAHF",

    # Other (7 is compulsory military service which doesn't exist in Ireland)
    8: "T8_1_OTH",

    # Child (left out of SAPs tables)
    9: ""
}


def employment_status(row):
    if isnan(row["MAINSTAT"]) or (row["MAINSTAT"] == ""):
        return "T8_1_OTH" + sexes[row["SEX"]]
    elif row["MAINSTAT"] == 9:
        return "T8_1_NA"
    else:
        return saps_employment_statuses[row["MAINSTAT"]] + sexes[row["SEX"]]


def trimmed_employment_status(row):
    possibly_gendered_status = employment_status(row).split("T8_1_")[1]
    if possibly_gendered_status[-1] in ["M", "F"]:
        return possibly_gendered_status[:-1]
    else:
        return possibly_gendered_status


def highest_level_of_education(row):
    childrens_ages = ["T1_1AGE0_4M",
                      "T1_1AGE5_9M",
                      "T1_1AGE10_14M",
                      "T1_1AGE0_4F",
                      "T1_1AGE5_9F",
                      "T1_1AGE10_14F"]
    if row["HATLEVEL"]==999:
        return "T10_4_NA"
    elif (row["T1_1"] in childrens_ages) or ("T8_1_S" in row["T8_1"]):
        return "T10_4_NA"
    elif isnan(row["HATLEVEL"]) or (row["HATLEVEL"] == ""):
        return "T10_4_NS" + sexes[row["SEX"]]
    else:
        return saps_levels_of_education[row["HATLEVEL"]] + sexes[row["SEX"]]


def trimmed_education(row):
    possibly_gendered_education = highest_level_of_education(row).split("T10_4_")[1]
    if possibly_gendered_education[-1] in ["M", "F"]:
        return possibly_gendered_education[:-1]
    else:
        return possibly_gendered_education
