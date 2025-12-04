import pickle as pkl
import random

import pandas as pd

import relationships
from constants import regions_counties, school_enrollment_age, single_year_age_proportions_within_age_group_2022
from individual import Individual

ed_names_dataset = pd.read_csv("eds_counties_and_regions.csv")
ed_names_dataset["ED_ID"] = ed_names_dataset["ED_ID"].astype(str)

old_women_2016 = [0.15906477577615946, 0.1429441075011837, 0.12612450116113905, 0.10840303925326358, 0.09663382409307149, 0.08330890807837125, 0.06874394065790364, 0.055261199918833, 0.04466439699682096, 0.034676346583094715, 0.026176357856289315, 0.019931008049060943, 0.01217505016571596, 0.008026514553694226, 0.013866029355398733]
old_men_2016 = [0.21022628372497823, 0.17193211488250654, 0.1376414273281114, 0.11127067014795475, 0.09208006962576153, 0.07254134029590949, 0.05748476936466493, 0.041906005221932115, 0.032463011314186246, 0.022758920800696258, 0.016840731070496082, 0.013794604003481288, 0.008268059181897302, 0.004046997389033942, 0.006744995648389904]


def translate_characteristics_from_cso_code_to_readable_individual(person: [str],
                                                                   ed_id,
                                                                   start_year: int = 2022):
    age_and_sex = person[0]
    sex = age_and_sex[-1]

    age_range = age_and_sex.split("AGE")[1][:-1]
    if age_range != "GE_85":
        relevant_dict = single_year_age_proportions_within_age_group_2022[sex][age_range]
        age = random.choices(list(relevant_dict.keys()),
                             weights=list(relevant_dict.values()),
                             k=1)[0]
    else:
        if sex == "F":
            sexs_old_people_weights = old_women_2016
        else:
            sexs_old_people_weights = old_men_2016
        age = random.choices(range(85, 100), k=1, weights=sexs_old_people_weights)[0]

    marital_status = person[1].split("2")[1][:-1]  # Leave out sex

    citizenship = person[2][-3:-1]

    moved_to_ireland_in_last_year = True if person[3][-2:] == "OI" else False

    # if person[3][-2:] != "NA":  # Child
    if person[4][-2:] != "NA":  # Child
        economic_status = person[4].split("1_")[1][:-1]  # Leave out sex
    elif school_enrollment_age <= age <= 15:  # Assume kids are in school
        economic_status = "S"
    else:
        economic_status = "NA"

    # if person[4][-2:] != "NA":  # Child, student, etc.
    if person[5][-2:] != "NA":  # Child, student, etc.
        education = person[5].split("4_")[1][:-1]  # Leave out sex
    else:
        education = "NA"

    return Individual(age=age,
                      sex=sex,
                      marital_status=marital_status,
                      citizenship=citizenship,
                      moved_to_ireland_in_last_year=moved_to_ireland_in_last_year,
                      economic_status=economic_status,
                      education=education,
                      ed=ed_id,
                      born_in_simulation=False,
                      current_year=start_year)


def create_eds_individuals_from_population(population_folder: str, ed_id: str, start_year: int = 2022):
    file = population_folder + ed_id + ".pkl"

    eds_row = ed_names_dataset[ed_names_dataset["ED_ID"] == ed_id]

    ed_english = eds_row["ENGLISH"].values[0]
    county = eds_row["COUNTY"].values[0].title()
    for higher_region, counties in regions_counties.items():
        if county in counties:
            region = higher_region.title()
            break

    with open(file, 'rb') as f:
        eds_population = pkl.load(f)

    # Combinatorial Optimisation populations stored as list of dicts
    if isinstance(eds_population[0], dict):
        population_as_individuals = [
            translate_characteristics_from_cso_code_to_readable_individual(person, ed_id, start_year)
            for household in eds_population for _, person in household.items()]

        idx_tracker = 0
        for household in eds_population:
            people_in_house_count = len(household)

            married_people_in_house = list(filter(lambda person: person.marital_status == "MAR",
                                                  population_as_individuals
                                                  [idx_tracker:idx_tracker + people_in_house_count]))

            # TODO: Find a better way of doing this than random people in the same house
            while len(married_people_in_house) > 1:
                first_person_to_marry = married_people_in_house.pop(random.randrange(len(married_people_in_house)))
                second_person_to_marry = married_people_in_house.pop(random.randrange(len(married_people_in_house)))

                first_person_to_marry.spouse = second_person_to_marry
                second_person_to_marry.spouse = first_person_to_marry

            idx_tracker += people_in_house_count

    else:
        population_as_individuals = [translate_characteristics_from_cso_code_to_readable_individual(person, ed_id, start_year=start_year)
                                     for person in eds_population]

        married_pop_in_ed = [person for person in population_as_individuals if (person.marital_status == "MAR")
                             and (not hasattr(person, "spouse"))]
        relationships.match_couples_to_be_married_in_region_no_specified_sexualities(married_pop_in_ed,
                                                                                     marry_to_outsiders=False,
                                                                                     verbose=False)

    # sort_out_ns_citizenship(population_as_individuals)

    return population_as_individuals


if __name__ == '__main__':
    # folder = "./populations/ipf/"
    # folder = "./populations/new_ipf/"
    folder = "./populations/ipf_no_zero_cells_less_iter/"

    ed = "68013"  # Newcastle

    pop = create_eds_individuals_from_population(folder, ed)
    for human in pop:
        print(human)
