import random
from individual import Individual
from tqdm import tqdm
from collections import Counter
import numpy as np
import pickle as pkl
from place_v2 import Place
from constants import regions, \
    international_emigration_proportions, \
    county_emigrants_by_county_2022, \
    county_emigrants_by_county_2016, \
    county_emigrants_by_county_average, \
    actual_international_immigration, \
    actual_international_emigration, \
    number_of_within_county_migrants, \
    proportion_of_counties_immigrants_from_same_county_stripped_ids, \
    proportion_of_counties_immigrants_from_different_county_stripped_ids, \
    proportion_of_countries_international_immigrants_stripped_ids, \
    new_cso_international_migration, within_county_migrant_proportions, different_county_migration_proportions, \
    emigration_proportions_2017_2022_average, \
    immigration_proportions_2017_2022_average, citizenship_of_international_immigrants_2017_2022_average, \
    citizenship_of_international_emigrants_2017_2022_average, \
    regional_proportion_of_countries_international_immigrants_2022, csos_net_international_migration, \
    cso_international_migration_from_regional_projections

with open('ireland_population_2022.pkl', 'rb') as f:
    population_from_2022_census = pkl.load(f)
recent_immigrants_from_2022_census = [person_2022 for person_2022 in population_from_2022_census
                                      if person_2022.moved_to_ireland_in_last_year]

recent_immigrant_pre_immigration_cohort_populations = {}

for person in recent_immigrants_from_2022_census:
    if person.age > 0:
        if 0 <= person.age <= 14:
            age_label = "0 - 14 years"
        elif 15 <= person.age <= 24:
            age_label = "15 - 24 years"
        elif 25 <= person.age <= 44:
            age_label = "25 - 44 years"
        elif 45 <= person.age <= 64:
            age_label = "45 - 64 years"
        else:  # person.age >= 65:
            age_label = "65 years and over"

        if (person.sex, age_label, person.citizenship) not in recent_immigrant_pre_immigration_cohort_populations:
            recent_immigrant_pre_immigration_cohort_populations[(person.sex, age_label, person.citizenship)] = [person]
        else:
            recent_immigrant_pre_immigration_cohort_populations[(person.sex, age_label, person.citizenship)].append(person)


def distribute_within_county_realistic_migrants_unique_destination_origin(county: str, countys_eds: dict[str, Place]):
    num_migrants_to_distribute_in_county = number_of_within_county_migrants[county]

    countys_ed_ids = list(countys_eds.keys())

    eds_cohort_populations = {}
    for ed_id, ed_object in countys_eds.items():
        eds_cohort_populations[ed_id] = {}
        for person in ed_object.population:
            if person.age > 0:
                if person.age >= 85:
                    age_label = "85 years and over"
                elif 1 <= person.age < 5:
                    age_label = "1 - 4 years"
                else:
                    lower_label = person.age - (person.age % 5)
                    age_label = f"{lower_label} - {lower_label + 4} years"

                if (person.sex, age_label) not in eds_cohort_populations[ed_id]:
                    eds_cohort_populations[ed_id][(person.sex, age_label)] = [person]
                else:
                    eds_cohort_populations[ed_id][(person.sex, age_label)].append(person)

    eds_new_people = {}
    for destination_ed_id, proportion in proportion_of_counties_immigrants_from_same_county_stripped_ids[county].items():
        if destination_ed_id in countys_eds:  # TODO: Remove this for whole island simulation
            num_migrants_to_move_to_ed = round(proportion * num_migrants_to_distribute_in_county)

            countys_ed_ids_without_this_destination = [c for c in countys_ed_ids if c != destination_ed_id]
            countys_ed_ids_without_this_destination_populations = [len(countys_eds[not_this_ed_id].population) for
                                                                   not_this_ed_id in
                                                                   countys_ed_ids_without_this_destination]

            # First sample migrant origins according to their ED population
            where_to_take_migrants_to_ed_from = random.choices(countys_ed_ids_without_this_destination,
                                                               weights=countys_ed_ids_without_this_destination_populations,
                                                               k=num_migrants_to_move_to_ed)

            origin_ed_counter = Counter(where_to_take_migrants_to_ed_from)

            eds_new_people[destination_ed_id] = []
            for migrants_origin_ed, num_migrants_from_origin_ed in origin_ed_counter.items():
                valid_proportions = {k: v for k, v in within_county_migrant_proportions[county].items()
                                     if (k in eds_cohort_populations[migrants_origin_ed]) and
                                     (len(eds_cohort_populations[migrants_origin_ed][k]) > 0)}

                # Then, sample the origin ED's population according to the cohort proportions
                migrants_from_origin_ed_cohorts = random.choices(list(valid_proportions.keys()),
                                                                 list(valid_proportions.values()),
                                                                 k=num_migrants_from_origin_ed)

                migrants_from_origin_ed_cohort_counter = Counter(migrants_from_origin_ed_cohorts)

                while len(migrants_from_origin_ed_cohort_counter) > 0:
                    (sex, age_group), num_migrants_in_cohort = random.choice(list(migrants_from_origin_ed_cohort_counter.items()))

                    if ((sex, age_group) not in eds_cohort_populations[migrants_origin_ed]) or \
                            (num_migrants_in_cohort > len(eds_cohort_populations[migrants_origin_ed][(sex, age_group)])):

                        print(f"Old migrants counter: {migrants_from_origin_ed_cohort_counter}")
                        if (sex, age_group) not in eds_cohort_populations[migrants_origin_ed]:
                            num_replacements = num_migrants_in_cohort
                            chosen_candidates_indices = []

                            # Remove it from the possibilities list if it's not in there
                            del migrants_from_origin_ed_cohort_counter[(sex, age_group)]
                        else:
                            num_replacements = num_migrants_in_cohort - len(eds_cohort_populations[migrants_origin_ed][(sex, age_group)])
                            chosen_candidates_indices = range(len(eds_cohort_populations[migrants_origin_ed][(sex, age_group)]))

                            migrants_from_origin_ed_cohort_counter[(sex, age_group)] -= num_replacements

                        if num_replacements > 0:
                            valid_proportions = {k: v for k, v in within_county_migrant_proportions[county].items()
                                                 if k in eds_cohort_populations[migrants_origin_ed] and
                                                 (len(eds_cohort_populations[migrants_origin_ed][k]) > 0)
                                                 and (k != (sex, age_group))}

                            print(f"Replacing {num_replacements} individuals from {(sex, age_group)}")
                            print(f"Valid proportions remaining: {valid_proportions}")
                            if len(valid_proportions) > 0:
                                for k in valid_proportions.keys():
                                    print(f"Number of individuals remaining in {k}: "
                                          f"{len(eds_cohort_populations[migrants_origin_ed][k])}")

                            replacement_cohorts = random.choices(list(valid_proportions.keys()),
                                                                 list(valid_proportions.values()),
                                                                 k=num_replacements)

                            for (replacement_sex, replacement_age_group) in replacement_cohorts:
                                if (replacement_sex, replacement_age_group) in migrants_from_origin_ed_cohort_counter:
                                    migrants_from_origin_ed_cohort_counter[(replacement_sex, replacement_age_group)] += 1
                                else:
                                    migrants_from_origin_ed_cohort_counter[(replacement_sex, replacement_age_group)] = 1

                            print(f"Updated migrants counter: {migrants_from_origin_ed_cohort_counter}\n")
                    else:
                        chosen_candidates_indices = np.random.choice(
                            range(len(eds_cohort_populations[migrants_origin_ed][(sex, age_group)])),
                            size=num_migrants_in_cohort,
                            replace=False)

                    for chosen_candidate_idx in sorted(chosen_candidates_indices, reverse=True):
                        chosen_candidate = eds_cohort_populations[migrants_origin_ed][(sex, age_group)]\
                            .pop(chosen_candidate_idx)

                        # Remove them from their origin ED
                        countys_eds[chosen_candidate.ed].population.remove(chosen_candidate)

                        if len(eds_cohort_populations[migrants_origin_ed][(sex, age_group)]) == 0:
                            del eds_cohort_populations[migrants_origin_ed][(sex, age_group)]

                        migrants_from_origin_ed_cohort_counter[(sex, age_group)] -= 1
                        if migrants_from_origin_ed_cohort_counter[(sex, age_group)] == 0:
                            del migrants_from_origin_ed_cohort_counter[(sex, age_group)]

                        chosen_candidate.ed = destination_ed_id
                        eds_new_people[destination_ed_id].append(chosen_candidate)

    # When all EDs are done, move migrants to their new EDs
    for destination_ed_id, people_to_move_in in eds_new_people.items():
        countys_eds[destination_ed_id].add_people_to_places_population(people_to_move_in)


# Need to have people removed from their current ED before using this function
def distribute_migrants_from_other_counties(migrants_to_destination_county, countys_eds: dict[str, Place], destination_county:str):
    num_migrants_coming_into_county = len(migrants_to_destination_county)

    destinations = random.choices(list(proportion_of_counties_immigrants_from_different_county_stripped_ids[destination_county].keys()),
                                  list(proportion_of_counties_immigrants_from_different_county_stripped_ids[destination_county].values()),
                                  k=num_migrants_coming_into_county)

    destination_ed_migrant_counts = Counter(destinations)

    for destination_ed_id, num_migrants_to_ed in destination_ed_migrant_counts.items():
        migrants_to_ed = [migrants_to_destination_county.pop(random.randrange(len(migrants_to_destination_county))) for
                          _ in range(num_migrants_to_ed)]

        countys_eds[destination_ed_id].add_people_to_places_population(migrants_to_ed)


def distribute_international_immigrants_to_eds(international_immigrants, eds: dict[str, Place]):
    num_migrants_coming_into_country = len(international_immigrants)

    destinations = random.choices(list(proportion_of_countries_international_immigrants_stripped_ids.keys()),
                                  list(proportion_of_countries_international_immigrants_stripped_ids.values()),
                                  k=num_migrants_coming_into_country)

    destination_ed_migrant_counts = Counter(destinations)

    for destination_ed_id, num_migrants_to_ed in tqdm(destination_ed_migrant_counts.items(), "Per ED International Immigrants"):
        migrants_to_ed = [international_immigrants.pop(random.randrange(len(international_immigrants))) for
                          _ in range(num_migrants_to_ed)]

        eds[destination_ed_id].add_people_to_places_population(migrants_to_ed, from_abroad=True)


def internal_migrants_ed_with_realistic_destination_proportions_and_migrants(dublin_outflow:bool, eds: dict[str, Place]):
    starting_populations = {}
    net_changes_in_eds_population = {}
    for ed_id, place in eds.items():
        starting_populations[ed_id] = len(place.population)

    # if dublin_outflow:
    #     emigrants_data = county_emigrants_by_county_2022
    # else:
    #     emigrants_data = county_emigrants_by_county_2016

    emigrants_data = county_emigrants_by_county_average

    # Key: Destination county, Value: List of people to move in
    people_to_move_into_county = {}

    for origin_county, destinations in tqdm(emigrants_data.items(), desc="County's Internal Migration Emigrants and Within County Migration"):
        # Get county's EDs
        origin_countys_eds = {ed_id: ed for ed_id, ed in eds.items() if ed.county == origin_county}

        origin_countys_eds_populations = {ed_id: len(ed.population) for ed_id, ed in origin_countys_eds.items()}

        # Move people within the county itself's EDs
        distribute_within_county_realistic_migrants_unique_destination_origin(origin_county, origin_countys_eds)

        origin_countys_whole_population = []
        for ed_id, ed_object in origin_countys_eds.items():
            origin_countys_whole_population.extend(ed_object.population)

        num_emigrants_to_different_counties = sum(destinations.values())

        cohort_peoples_eds_populations = {}
        for person in origin_countys_whole_population:
            if person.age > 0:
                if person.age >= 85:
                    age_label = "85 years and over"
                elif 1 <= person.age < 5:
                    age_label = "1 - 4 years"
                else:
                    lower_label = person.age - (person.age % 5)
                    age_label = f"{lower_label} - {lower_label + 4} years"

                if (person.sex, age_label) not in cohort_peoples_eds_populations:
                    cohort_peoples_eds_populations[(person.sex, age_label)] = {person: origin_countys_eds_populations[person.ed]}
                else:
                    cohort_peoples_eds_populations[(person.sex, age_label)][person] = origin_countys_eds_populations[person.ed]

        valid_proportions = {k: v for k, v in different_county_migration_proportions[origin_county].items()
                             if k in cohort_peoples_eds_populations}

        emigrants_cohorts = random.choices(list(valid_proportions.keys()),
                                           list(valid_proportions.values()),
                                           k=num_emigrants_to_different_counties)

        emigrant_cohort_counter = Counter(emigrants_cohorts)

        people_to_move_from_origin_county = []

        while len(emigrant_cohort_counter) > 0:
            (sex, age_group), num_emigrants_in_cohort = random.choice(list(emigrant_cohort_counter.items()))

            if ((sex, age_group) not in cohort_peoples_eds_populations) or \
                    (num_emigrants_in_cohort > len(cohort_peoples_eds_populations[(sex, age_group)])):
                if (sex, age_group) not in cohort_peoples_eds_populations:
                    num_replacements = num_emigrants_in_cohort
                    chosen_candidates = []

                    del emigrant_cohort_counter[(sex, age_group)]
                else:
                    num_replacements = num_emigrants_in_cohort - len(cohort_peoples_eds_populations[(sex, age_group)])
                    chosen_candidates = list(cohort_peoples_eds_populations[(sex, age_group)].keys())

                    emigrant_cohort_counter[(sex, age_group)] -= num_replacements

                if num_replacements > 0:
                    valid_proportions = {k: v for k, v in different_county_migration_proportions[origin_county].items()
                                         if (k in cohort_peoples_eds_populations) and (k != (sex, age_group))}

                    replacement_cohorts = random.choices(list(valid_proportions.keys()),
                                                         list(valid_proportions.values()),
                                                         k=num_replacements)

                    for (replacement_sex, replacement_age_group) in replacement_cohorts:
                        if (replacement_sex, replacement_age_group) in emigrant_cohort_counter:
                            emigrant_cohort_counter[(replacement_sex, replacement_age_group)] += 1
                        else:
                            emigrant_cohort_counter[(replacement_sex, replacement_age_group)] = 1
            else:
                total_pops_of_cohort = sum(list(cohort_peoples_eds_populations[(sex, age_group)].values()))
                normalised_cohort_peoples_eds_populations = {k: v / total_pops_of_cohort for k, v in
                                                             cohort_peoples_eds_populations[(sex, age_group)].items()}
                chosen_candidates = np.random.choice(list(normalised_cohort_peoples_eds_populations.keys()),
                                                 size=num_emigrants_in_cohort,
                                                 replace=False,
                                                 p=list(normalised_cohort_peoples_eds_populations.values()))

            for chosen_candidate in chosen_candidates:
                del cohort_peoples_eds_populations[(sex, age_group)][chosen_candidate]

                # Remove them from their origin ED
                eds[chosen_candidate.ed].population.remove(chosen_candidate)

                if len(cohort_peoples_eds_populations[(sex, age_group)]) == 0:
                    del cohort_peoples_eds_populations[(sex, age_group)]
                    del valid_proportions[(sex, age_group)]

                emigrant_cohort_counter[(sex, age_group)] -= 1
                if emigrant_cohort_counter[(sex, age_group)] == 0:
                    del emigrant_cohort_counter[(sex, age_group)]

                people_to_move_from_origin_county.append(chosen_candidate)

        # Shuffle to avoid sampling the same people to the same ED every time
        random.shuffle(people_to_move_from_origin_county)

        for destination_county, num_emigrants_to_destination_county in destinations.items():
            if destination_county not in people_to_move_into_county:
                people_to_move_into_county[destination_county] = []

            if num_emigrants_to_destination_county > 0:
                for _ in range(num_emigrants_to_destination_county):
                    people_to_move_into_county[destination_county].append(
                        people_to_move_from_origin_county.pop(random.randrange(len(people_to_move_from_origin_county)))
                    )

    # Add migrants to destination population at the end
    for destination_county, destination_county_immigrants in tqdm(people_to_move_into_county.items(), desc="County's Internal Migration Immigrants"):
        destination_countys_eds = {ed_id: ed for ed_id, ed in eds.items() if ed.county == destination_county}
        distribute_migrants_from_other_counties(destination_county_immigrants, destination_countys_eds, destination_county)

    ending_populations = {}
    for name, place in eds.items():
        ending_populations[name] = len(place.population)

    for name in eds.keys():
        net_changes_in_eds_population[name] = ending_populations[name] - starting_populations[name]

    return net_changes_in_eds_population


def international_migration_eds_with_csos_average_realistic_proportions(international_migration_scenario: str,
                                                                        eds: dict[str, Place],
                                                                        current_year: int):
    regional_net_international_migration = {}
    if international_migration_scenario == "M1":
        num_immigrants_state = 80_000
        num_emigrants_state = 50_000
    elif international_migration_scenario == "custom":
        num_immigrants_state = 100_000
        num_emigrants_state = 50_000
    elif international_migration_scenario == "M2":
        num_immigrants_state = 70_000
        num_emigrants_state = 50_000
    elif international_migration_scenario == "actual":
        num_immigrants_state = actual_international_immigration[current_year]
        num_emigrants_state = actual_international_emigration[current_year]
    elif "new" in international_migration_scenario:
        num_immigrants_state, num_emigrants_state = new_cso_international_migration(international_migration_scenario,
                                                                                    year=current_year)
    else:
        num_immigrants_state = 70_000
        num_emigrants_state = 60_000

    print(f"- Num. immigrants to Ireland: {num_immigrants_state}")
    print(f"- Num. emigrants from Ireland: {num_emigrants_state}")

    state_emigrant_cohort_counts = {}

    initial_ed_populations = {}
    for region in tqdm(regions, desc="Regional International Emigrants"):
        regions_eds = {ed_id: ed for ed_id, ed in eds.items() if ed.region == region}

        regions_eds_populations = {ed_id: len(ed.population) for ed_id, ed in regions_eds.items()}

        for ed_id_in_region, pop_in_region in regions_eds_populations.items():
            initial_ed_populations[ed_id_in_region] = pop_in_region

        origin_regions_whole_population = []
        for ed_id, ed_object in regions_eds.items():
            origin_regions_whole_population.extend(ed_object.population)

        num_emigrants_from_region = round(international_emigration_proportions[region] * num_emigrants_state)

        # cohort_populations = {}
        cohort_peoples_eds_populations = {}
        for person in origin_regions_whole_population:
            if person.age > 0:
                if 0 <= person.age <= 14:
                    age_label = "0 - 14 years"
                elif 15 <= person.age <= 24:
                    age_label = "15 - 24 years"
                elif 25 <= person.age <= 44:
                    age_label = "25 - 44 years"
                elif 45 <= person.age <= 64:
                    age_label = "45 - 64 years"
                else:  # person.age >= 65:
                    age_label = "65 years and over"

                if (person.sex, age_label) not in cohort_peoples_eds_populations:
                    cohort_peoples_eds_populations[(person.sex, age_label)] = {person: regions_eds_populations[person.ed]}
                else:
                    cohort_peoples_eds_populations[(person.sex, age_label)][person] = regions_eds_populations[person.ed]

        valid_proportions = {k: v for k, v in emigration_proportions_2017_2022_average.items()
                             if k in cohort_peoples_eds_populations}

        emigrants_cohorts = random.choices(list(valid_proportions.keys()),
                                           list(valid_proportions.values()),
                                           k=num_emigrants_from_region)

        emigrant_cohort_counter = Counter(emigrants_cohorts)

        while len(emigrant_cohort_counter) > 0:
            (sex, age_group), num_migrants_in_cohort = random.choice(list(emigrant_cohort_counter.items()))

            if ((sex, age_group) not in cohort_peoples_eds_populations) or \
                    (num_migrants_in_cohort > len(cohort_peoples_eds_populations[(sex, age_group)])):
                if (sex, age_group) not in cohort_peoples_eds_populations:
                    num_replacements = num_migrants_in_cohort
                    chosen_candidates = []

                    del emigrant_cohort_counter[(sex, age_group)]
                else:
                    num_replacements = num_migrants_in_cohort - len(cohort_peoples_eds_populations[(sex, age_group)])
                    chosen_candidates = list(cohort_peoples_eds_populations[(sex, age_group)].keys())

                    emigrant_cohort_counter[(sex, age_group)] -= num_replacements

                if num_replacements > 0:
                    valid_proportions = {k: v for k, v in emigration_proportions_2017_2022_average.items()
                                         if (k in cohort_peoples_eds_populations) and (k != (sex, age_group))}

                    replacement_cohorts = random.choices(list(valid_proportions.keys()),
                                                         list(valid_proportions.values()),
                                                         k=num_replacements)

                    for (replacement_sex, replacement_age_group) in replacement_cohorts:
                        if (replacement_sex, replacement_age_group) in emigrant_cohort_counter:
                            emigrant_cohort_counter[(replacement_sex, replacement_age_group)] += 1
                        else:
                            emigrant_cohort_counter[(replacement_sex, replacement_age_group)] = 1
            else:
                total_pops_of_cohort = sum(list(cohort_peoples_eds_populations[(sex, age_group)].values()))
                normalised_cohort_peoples_eds_populations = {k: v / total_pops_of_cohort for k, v in
                                                             cohort_peoples_eds_populations[(sex, age_group)].items()}
                chosen_candidates = np.random.choice(list(normalised_cohort_peoples_eds_populations.keys()),
                                                     size=num_migrants_in_cohort,
                                                     replace=False,
                                                     p=list(normalised_cohort_peoples_eds_populations.values()))

            for chosen_candidate in chosen_candidates:
                del cohort_peoples_eds_populations[(sex, age_group)][chosen_candidate]

                if (sex, age_group) in state_emigrant_cohort_counts:
                    state_emigrant_cohort_counts[(sex, age_group)] += 1
                else:
                    state_emigrant_cohort_counts[(sex, age_group)] = 1

                # Remove them from their origin ED
                eds[chosen_candidate.ed].population.remove(chosen_candidate)
                chosen_candidate.remove_references_to_and_from_person(emigrate=True)

                if len(cohort_peoples_eds_populations[(sex, age_group)]) == 0:
                    del cohort_peoples_eds_populations[(sex, age_group)]
                    del valid_proportions[(sex, age_group)]

                emigrant_cohort_counter[(sex, age_group)] -= 1
                if emigrant_cohort_counter[(sex, age_group)] == 0:
                    del emigrant_cohort_counter[(sex, age_group)]

    state_total_emigrants = sum(list(state_emigrant_cohort_counts.values()))
    print(f"\n{current_year} state emigrant proportions:")
    for cohort_label, count in state_emigrant_cohort_counts.items():
        print(f"\t{cohort_label}: {count / state_total_emigrants:.3f}")

    pre_immigration_population = []
    for ed_id, ed_object in eds.items():
        pre_immigration_population.extend(ed_object.population)

    pre_immigration_cohort_populations = {}
    for person in pre_immigration_population:
        if person.age > 0:
            if 0 <= person.age <= 14:
                age_label = "0 - 14 years"
            elif 15 <= person.age <= 24:
                age_label = "15 - 24 years"
            elif 25 <= person.age <= 44:
                age_label = "25 - 44 years"
            elif 45 <= person.age <= 64:
                age_label = "45 - 64 years"
            else:  # person.age >= 65:
                age_label = "65 years and over"

            if (person.sex, age_label) not in pre_immigration_cohort_populations:
                pre_immigration_cohort_populations[(person.sex, age_label)] = [person]
            else:
                pre_immigration_cohort_populations[(person.sex, age_label)].append(person)

    state_immigrant_cohort_counts = {}
    # Immigration done all in one
    international_immigrants = []

    for (sex, age_group), proportion in tqdm(immigration_proportions_2017_2022_average.items(),
                                             desc=f"Generating international immigrants in cohort"):

        num_immigrants_in_bracket = round(num_immigrants_state * proportion)

        pre_immigration_cohort = pre_immigration_cohort_populations[(sex, age_group)]

        if (sex, age_group) in state_immigrant_cohort_counts:
            state_immigrant_cohort_counts[(sex, age_group)] += num_immigrants_in_bracket
        else:
            state_immigrant_cohort_counts[(sex, age_group)] = num_immigrants_in_bracket

        international_immigrants.extend(
            create_realistic_immigrant_based_on_age_and_sex(pre_immigration_cohort,
                                                                           num_immigrants_in_bracket,
                                                                           current_year=current_year))
    distribute_international_immigrants_to_eds(international_immigrants, eds)

    state_total_immigrants = sum(list(state_immigrant_cohort_counts.values()))
    print(f"\n{current_year} state immigrant proportions:")
    for cohort_label, count in state_immigrant_cohort_counts.items():
        print(f"\t{cohort_label}: {count / state_total_immigrants:.3f}")

    for ed_id, ed in eds.items():
        regional_net_international_migration[ed_id] = len(eds[ed_id].population) - initial_ed_populations[ed_id]

    return regional_net_international_migration


def create_realistic_immigrant_based_on_age_and_sex(pre_immigration_cohort: [Individual],
                                                                   num_immigrants: int,
                                                                   current_year: int):
    donors = random.choices(pre_immigration_cohort, k=num_immigrants)

    # Do donor method
    immigrants = []
    for immigrant_idx in range(num_immigrants):

        immigrants.append(Individual(age=donors[immigrant_idx].age,
                                     sex=donors[immigrant_idx].sex,
                                     marital_status=donors[immigrant_idx].marital_status,
                                     economic_status=donors[immigrant_idx].economic_status,
                                     education=donors[immigrant_idx].education,
                                     current_year=current_year
                                     ))

    return immigrants


def international_migration_eds_with_csos_average_realistic_proportions_with_citizenship(
        international_migration_scenario: str,
        eds: dict[str, Place],
        current_year: int):
    regional_net_international_migration = {}
    if international_migration_scenario == "M1":
        num_immigrants_state = 80_000
        num_emigrants_state = 50_000
    elif international_migration_scenario == "custom":
        num_immigrants_state = 100_000
        num_emigrants_state = 50_000
    elif international_migration_scenario == "M2":
        num_immigrants_state = 70_000
        num_emigrants_state = 50_000
    elif international_migration_scenario == "actual":
        num_immigrants_state = actual_international_immigration[current_year]
        num_emigrants_state = actual_international_emigration[current_year]
    elif "new" in international_migration_scenario:
        num_immigrants_state, num_emigrants_state = new_cso_international_migration(international_migration_scenario,
                                                                                    year=current_year)
    else:
        num_immigrants_state = 70_000
        num_emigrants_state = 60_000

    # recent_immigrant_pre_immigration_population = []
    # for ed_id, ed_object in eds.items():
    #     for person in ed_object.population:
    #         if person.moved_to_ireland_in_last_year:
    #             recent_immigrant_pre_immigration_population.append(person)
    #         person.moved_to_ireland_in_last_year = False
    #     # pre_immigration_population.extend(ed_object.population)
    #
    # print(f"Number of recent immigrants: {len(recent_immigrant_pre_immigration_population)}")
    #
    # # Do this before emigration to ensure that all of the recent immigrants' characteristics are
    # # captured even if they emigrate
    # # pre_immigration_cohort_populations = {}
    # recent_immigrant_pre_immigration_cohort_populations = {}
    # # for person in pre_immigration_population:
    # for person in recent_immigrant_pre_immigration_population:
    #     # if person.age > 0:
    #     # if (person.age > 0) and person.moved_to_ireland_in_last_year:
    #     if person.age > 0:
    #         if 0 <= person.age <= 14:
    #             age_label = "0 - 14 years"
    #         elif 15 <= person.age <= 24:
    #             age_label = "15 - 24 years"
    #         elif 25 <= person.age <= 44:
    #             age_label = "25 - 44 years"
    #         elif 45 <= person.age <= 64:
    #             age_label = "45 - 64 years"
    #         else:  # person.age >= 65:
    #             age_label = "65 years and over"
    #
    #         # if (person.sex, age_label) not in pre_immigration_cohort_populations:
    #         #     pre_immigration_cohort_populations[(person.sex, age_label)] = [person]
    #         # else:
    #         #     pre_immigration_cohort_populations[(person.sex, age_label)].append(person)
    #
    #         if (person.sex, age_label, person.citizenship) not in recent_immigrant_pre_immigration_cohort_populations:
    #             recent_immigrant_pre_immigration_cohort_populations[(person.sex, age_label, person.citizenship)] = [person]
    #         else:
    #             recent_immigrant_pre_immigration_cohort_populations[(person.sex, age_label, person.citizenship)].append(person)

    print(f"- Num. immigrants to Ireland: {num_immigrants_state}")
    print(f"- Num. emigrants from Ireland: {num_emigrants_state}")

    state_emigrant_cohort_counts = {}

    emigration_proportions_with_citizenship = {}
    for (sex, age), sex_age_proportion in emigration_proportions_2017_2022_average.items():
        for citizenship, citizenship_proportion in citizenship_of_international_emigrants_2017_2022_average.items():
            emigration_proportions_with_citizenship[(sex, age, citizenship)] = sex_age_proportion * citizenship_proportion

    immigration_proportions_with_citizenship = {}
    for (sex, age), sex_age_proportion in immigration_proportions_2017_2022_average.items():
        for citizenship, citizenship_proportion in citizenship_of_international_immigrants_2017_2022_average.items():
            immigration_proportions_with_citizenship[(sex, age, citizenship)] = sex_age_proportion * citizenship_proportion

    initial_ed_populations = {}
    for region in tqdm(regions, desc="Regional International Emigrants"):
        regions_eds = {ed_id: ed for ed_id, ed in eds.items() if ed.region == region}

        regions_eds_populations = {ed_id: len(ed.population) for ed_id, ed in regions_eds.items()}

        for ed_id_in_region, pop_in_region in regions_eds_populations.items():
            initial_ed_populations[ed_id_in_region] = pop_in_region

        origin_regions_whole_population = []
        for ed_id, ed_object in regions_eds.items():
            origin_regions_whole_population.extend(ed_object.population)

        num_emigrants_from_region = round(international_emigration_proportions[region] * num_emigrants_state)

        # cohort_populations = {}
        cohort_peoples_eds_populations = {}
        for person in origin_regions_whole_population:
            if person.age > 0:
            # if person.age > 0 and (not person.moved_to_ireland_in_last_year):  # Assume people stay for at least one year
                if 0 <= person.age <= 14:
                    age_label = "0 - 14 years"
                elif 15 <= person.age <= 24:
                    age_label = "15 - 24 years"
                elif 25 <= person.age <= 44:
                    age_label = "25 - 44 years"
                elif 45 <= person.age <= 64:
                    age_label = "45 - 64 years"
                else:  # person.age >= 65:
                    age_label = "65 years and over"

                # if (person.sex, age_label) not in cohort_peoples_eds_populations:
                #     cohort_peoples_eds_populations[(person.sex, age_label)] = {person: regions_eds_populations[person.ed]}
                # else:
                #     cohort_peoples_eds_populations[(person.sex, age_label)][person] = regions_eds_populations[person.ed]

                if (person.sex, age_label, person.citizenship) not in cohort_peoples_eds_populations:
                    cohort_peoples_eds_populations[(person.sex, age_label, person.citizenship)] = {person: regions_eds_populations[person.ed]}
                else:
                    cohort_peoples_eds_populations[(person.sex, age_label, person.citizenship)][person] = regions_eds_populations[person.ed]

        # valid_proportions = {k: v for k, v in emigration_proportions_2017_2022_average.items()
        #                      if k in cohort_peoples_eds_populations}
        valid_proportions = {k: v for k, v in emigration_proportions_with_citizenship.items()
                             if k in cohort_peoples_eds_populations}

        emigrants_cohorts = random.choices(list(valid_proportions.keys()),
                                           list(valid_proportions.values()),
                                           k=num_emigrants_from_region)

        emigrant_cohort_counter = Counter(emigrants_cohorts)

        while len(emigrant_cohort_counter) > 0:
            # (sex, age_group), num_migrants_in_cohort = random.choice(list(emigrant_cohort_counter.items()))
            (sex, age_group, citizenship), num_migrants_in_cohort = random.choice(list(emigrant_cohort_counter.items()))

            # if ((sex, age_group) not in cohort_peoples_eds_populations) or \
            #         (num_migrants_in_cohort > len(cohort_peoples_eds_populations[(sex, age_group)])):
            if ((sex, age_group, citizenship) not in cohort_peoples_eds_populations) or \
                    (num_migrants_in_cohort > len(cohort_peoples_eds_populations[(sex, age_group, citizenship)])):
                # if (sex, age_group) not in cohort_peoples_eds_populations:
                if (sex, age_group, citizenship) not in cohort_peoples_eds_populations:
                    num_replacements = num_migrants_in_cohort
                    chosen_candidates = []

                    del emigrant_cohort_counter[(sex, age_group, citizenship)]
                else:
                    # num_replacements = num_migrants_in_cohort - len(cohort_peoples_eds_populations[(sex, age_group)])
                    # chosen_candidates = list(cohort_peoples_eds_populations[(sex, age_group)].keys())
                    num_replacements = num_migrants_in_cohort - len(cohort_peoples_eds_populations[(sex, age_group, citizenship)])
                    chosen_candidates = list(cohort_peoples_eds_populations[(sex, age_group, citizenship)].keys())

                    # emigrant_cohort_counter[(sex, age_group)] -= num_replacements
                    emigrant_cohort_counter[(sex, age_group, citizenship)] -= num_replacements

                if num_replacements > 0:
                    # valid_proportions = {k: v for k, v in emigration_proportions_2017_2022_average.items()
                    #                      if (k in cohort_peoples_eds_populations) and (k != (sex, age_group))}
                    valid_replacement_proportions = {k: v for k, v in emigration_proportions_with_citizenship.items()
                                         if (k in cohort_peoples_eds_populations) and (k != (sex, age_group, citizenship))}

                    replacement_cohorts = random.choices(list(valid_replacement_proportions.keys()),
                                                         list(valid_replacement_proportions.values()),
                                                         k=num_replacements)

                    # for (replacement_sex, replacement_age_group) in replacement_cohorts:
                    #     if (replacement_sex, replacement_age_group) in emigrant_cohort_counter:
                    #         emigrant_cohort_counter[(replacement_sex, replacement_age_group)] += 1
                    #     else:
                    #         emigrant_cohort_counter[(replacement_sex, replacement_age_group)] = 1
                    for (replacement_sex, replacement_age_group, replacement_citizenship) in replacement_cohorts:
                        if (replacement_sex, replacement_age_group, replacement_citizenship) in emigrant_cohort_counter:
                            emigrant_cohort_counter[(replacement_sex, replacement_age_group, replacement_citizenship)] += 1
                        else:
                            emigrant_cohort_counter[(replacement_sex, replacement_age_group, replacement_citizenship)] = 1
            else:
                # total_pops_of_cohort = sum(list(cohort_peoples_eds_populations[(sex, age_group)].values()))
                # normalised_cohort_peoples_eds_populations = {k: v / total_pops_of_cohort for k, v in
                #                                              cohort_peoples_eds_populations[(sex, age_group)].items()}
                total_pops_of_cohort = sum(list(cohort_peoples_eds_populations[(sex, age_group, citizenship)].values()))
                normalised_cohort_peoples_eds_populations = {k: v / total_pops_of_cohort for k, v in
                                                             cohort_peoples_eds_populations[(sex, age_group, citizenship)].items()}
                chosen_candidates = np.random.choice(list(normalised_cohort_peoples_eds_populations.keys()),
                                                     size=num_migrants_in_cohort,
                                                     replace=False,
                                                     p=list(normalised_cohort_peoples_eds_populations.values()))

            for chosen_candidate in chosen_candidates:
                # del cohort_peoples_eds_populations[(sex, age_group)][chosen_candidate]
                del cohort_peoples_eds_populations[(sex, age_group, citizenship)][chosen_candidate]

                # if (sex, age_group) in state_emigrant_cohort_counts:
                #     state_emigrant_cohort_counts[(sex, age_group)] += 1
                # else:
                #     state_emigrant_cohort_counts[(sex, age_group)] = 1
                if (sex, age_group, citizenship) in state_emigrant_cohort_counts:
                    state_emigrant_cohort_counts[(sex, age_group, citizenship)] += 1
                else:
                    state_emigrant_cohort_counts[(sex, age_group, citizenship)] = 1

                # Remove them from their origin ED
                eds[chosen_candidate.ed].population.remove(chosen_candidate)
                chosen_candidate.remove_references_to_and_from_person(emigrate=True)

                # if len(cohort_peoples_eds_populations[(sex, age_group)]) == 0:
                #     del cohort_peoples_eds_populations[(sex, age_group)]
                #     del valid_proportions[(sex, age_group)]
                #
                # emigrant_cohort_counter[(sex, age_group)] -= 1
                # if emigrant_cohort_counter[(sex, age_group)] == 0:
                #     del emigrant_cohort_counter[(sex, age_group)]

                if len(cohort_peoples_eds_populations[(sex, age_group, citizenship)]) == 0:
                    del cohort_peoples_eds_populations[(sex, age_group, citizenship)]
                    # try:
                    #     del valid_proportions[(sex, age_group, citizenship)]
                    # except KeyError:
                    #     print("Got that key error on del valid proportions")

                emigrant_cohort_counter[(sex, age_group, citizenship)] -= 1
                if emigrant_cohort_counter[(sex, age_group, citizenship)] == 0:
                    del emigrant_cohort_counter[(sex, age_group, citizenship)]

    state_total_emigrants = sum(list(state_emigrant_cohort_counts.values()))
    print(f"\n{current_year} state emigrant proportions:")
    for cohort_label, count in state_emigrant_cohort_counts.items():
        print(f"\t{cohort_label}: {count / state_total_emigrants:.3f}")

    # pre_immigration_population = []
    state_immigrant_cohort_counts = {}
    # Immigration done all in one
    international_immigrants = []

    # recent_immigrant_pre_immigration_population = []
    for ed_id, ed_object in eds.items():
        for person in ed_object.population:
            if person.moved_to_ireland_in_last_year:
                # recent_immigrant_pre_immigration_population.append(person)
                person.moved_to_ireland_in_last_year = False
        # pre_immigration_population.extend(ed_object.population)

    # print(f"Number of recent immigrants: {len(recent_immigrant_pre_immigration_population)}")

    # Do this before emigration to ensure that all of the recent immigrants' characteristics are
    # captured even if they emigrate
    # pre_immigration_cohort_populations = {}
    # recent_immigrant_pre_immigration_cohort_populations = {}
    # # for person in pre_immigration_population:
    # # for person in recent_immigrant_pre_immigration_population:
    # for person in recent_immigrants_from_2022_census:
    #     # if person.age > 0:
    #     # if (person.age > 0) and person.moved_to_ireland_in_last_year:
    #     if person.age > 0:
    #         if 0 <= person.age <= 14:
    #             age_label = "0 - 14 years"
    #         elif 15 <= person.age <= 24:
    #             age_label = "15 - 24 years"
    #         elif 25 <= person.age <= 44:
    #             age_label = "25 - 44 years"
    #         elif 45 <= person.age <= 64:
    #             age_label = "45 - 64 years"
    #         else:  # person.age >= 65:
    #             age_label = "65 years and over"
    #
    #         # if (person.sex, age_label) not in pre_immigration_cohort_populations:
    #         #     pre_immigration_cohort_populations[(person.sex, age_label)] = [person]
    #         # else:
    #         #     pre_immigration_cohort_populations[(person.sex, age_label)].append(person)
    #
    #         if (person.sex, age_label, person.citizenship) not in recent_immigrant_pre_immigration_cohort_populations:
    #             recent_immigrant_pre_immigration_cohort_populations[(person.sex, age_label, person.citizenship)] = [person]
    #         else:
    #             recent_immigrant_pre_immigration_cohort_populations[(person.sex, age_label, person.citizenship)].append(person)

    # for (sex, age_group), proportion in tqdm(immigration_proportions_2017_2022_average.items(),
    #                                          desc=f"Generating international immigrants in cohort"):
    for (sex, age_group, citizenship), proportion in tqdm(immigration_proportions_with_citizenship.items(),
                                             desc=f"Generating international immigrants in cohort"):

        num_immigrants_in_bracket = round(num_immigrants_state * proportion)

        # pre_immigration_cohort = pre_immigration_cohort_populations[(sex, age_group)]
        # pre_immigration_cohort = pre_immigration_cohort_populations[(sex, age_group, citizenship)]
        try:
            recent_immigrant_pre_immigration_cohort = recent_immigrant_pre_immigration_cohort_populations[(sex, age_group, citizenship)]
        except KeyError:  # Sex, age group, citizenship not in recent immigrants
            # Swap to a different citizenship
            # For people who aren't in the dictionary, assume citizenship is the problem
            print("Somehow didn't find the right cohort")
            possible_citizenships = list(citizenship_of_international_immigrants_2017_2022_average.keys())
            random.shuffle(possible_citizenships)
            for other_citizenship in possible_citizenships:
                if other_citizenship != citizenship:
                    possible_new_key = (sex, age_group, other_citizenship)
                    if possible_new_key in recent_immigrant_pre_immigration_cohort_populations:
                        recent_immigrant_pre_immigration_cohort = recent_immigrant_pre_immigration_cohort_populations[possible_new_key]

                        # No need to look at other citizenships, this one worked
                        break
                    elif other_citizenship == possible_citizenships[-1]:
                        # If we reached here, no citizenships worked
                        raise KeyError(f"None of the possible citizenships worked for {(sex, age_group)}")

        # if (sex, age_group) in state_immigrant_cohort_counts:
        #     state_immigrant_cohort_counts[(sex, age_group)] += num_immigrants_in_bracket
        # else:
        #     state_immigrant_cohort_counts[(sex, age_group)] = num_immigrants_in_bracket
        if (sex, age_group, citizenship) in state_immigrant_cohort_counts:
            state_immigrant_cohort_counts[(sex, age_group, citizenship)] += num_immigrants_in_bracket
        else:
            state_immigrant_cohort_counts[(sex, age_group, citizenship)] = num_immigrants_in_bracket

        international_immigrants.extend(
            create_realistic_immigrant_from_same_cohort(recent_immigrant_pre_immigration_cohort,
                                                        num_immigrants_in_bracket,
                                                        current_year=current_year))
    distribute_international_immigrants_to_eds(international_immigrants, eds)

    state_total_immigrants = sum(list(state_immigrant_cohort_counts.values()))
    print(f"\n{current_year} state immigrant proportions:")
    for cohort_label, count in state_immigrant_cohort_counts.items():
        print(f"\t{cohort_label}: {count / state_total_immigrants:.3f}")

    for ed_id, ed in eds.items():
        regional_net_international_migration[ed_id] = len(eds[ed_id].population) - initial_ed_populations[ed_id]

    return regional_net_international_migration


def international_migration_eds_with_csos_average_realistic_proportions_with_citizenship_correct_net_migrations(
        international_migration_scenario: str,
        eds: dict[str, Place],
        current_year: int):
    regional_net_international_migration = {}

    # num_immigrants_state, num_emigrants_state = new_cso_international_migration(international_migration_scenario,
    #                                                                             year=current_year)
    num_immigrants_state, num_emigrants_state = cso_international_migration_from_regional_projections(
        international_migration_scenario,
        year=current_year)

    desired_net_migration_state = num_immigrants_state - num_emigrants_state

    print(f"- Num. immigrants to Ireland: {num_immigrants_state}")
    regional_num_immigrants = {}
    for region, proportion_of_states_immigrants in regional_proportion_of_countries_international_immigrants_2022.items():
        regional_num_immigrants[region] = round(proportion_of_states_immigrants * num_immigrants_state)

    regional_num_emigrants = {}
    trimmed_scenario = international_migration_scenario[-2:]
    if (current_year - 2022) % 5 == 0:
        # For years across two intercensal periods, have to get the average of the values
        total_net_migration_amongst_intercensal_periods = 0
        regions_total_net_migration_values = {}
        for _, (five_year_group, regions_values) in enumerate(csos_net_international_migration[f'Method - {trimmed_scenario}'].items()):
            split_years = five_year_group.split(' - ')
            five_year_group_lower = int(split_years[0])
            five_year_group_upper = int(split_years[1])

            if five_year_group_lower <= current_year <= five_year_group_upper:
                five_years_total = sum(regions_values.values())
                total_net_migration_amongst_intercensal_periods += five_years_total
                for region, value in regions_values.items():
                    if region not in regions_total_net_migration_values:
                        regions_total_net_migration_values[region] = 0
                    regions_total_net_migration_values[region] += value

        average_regional_net_migration = {region: round(
            (desired_net_migration_state / (total_net_migration_amongst_intercensal_periods / 2)) * (
                    regions_total_value / 2)) for region, regions_total_value in
            regions_total_net_migration_values.items()}

        for region, regions_net_migration in average_regional_net_migration.items():
            # Scale each regional net migration by the ratio of the desired national net migration to the CSO's
            # average net migration for the time period
            regional_num_emigrants[region] = regional_num_immigrants[region] - average_regional_net_migration[region]
    else:
        for five_year_group, each_regions_net_migration in csos_net_international_migration[f'Method - {trimmed_scenario}'].items():
            split_years = five_year_group.split(' - ')
            five_year_group_lower = int(split_years[0])
            five_year_group_upper = int(split_years[1])

            # if five_year_group_lower <= current_year < five_year_group_upper:
            if five_year_group_lower < current_year < five_year_group_upper:
                csos_average_net_migration_state = sum(each_regions_net_migration.values())
                for region, regions_net_migration in each_regions_net_migration.items():
                    # Scale each regional net migration by the ratio of the desired national net migration to the CSO's
                    # average net migration for the time period
                    regional_num_emigrants[region] = regional_num_immigrants[region] - round(
                                regions_net_migration * (desired_net_migration_state / csos_average_net_migration_state))
                # This is the only one that will work so we can stop looping
                break

    # print(f"- Num. emigrants from Ireland: {num_emigrants_state}")
    num_emigrants_state = sum(regional_num_emigrants.values())
    print(f"- Num. emigrants from Ireland: {num_emigrants_state}")

    state_emigrant_cohort_counts = {}

    emigration_proportions_with_citizenship = {}
    for (sex, age), sex_age_proportion in emigration_proportions_2017_2022_average.items():
        for citizenship, citizenship_proportion in citizenship_of_international_emigrants_2017_2022_average.items():
            emigration_proportions_with_citizenship[(sex, age, citizenship)] = sex_age_proportion * citizenship_proportion

    immigration_proportions_with_citizenship = {}
    for (sex, age), sex_age_proportion in immigration_proportions_2017_2022_average.items():
        for citizenship, citizenship_proportion in citizenship_of_international_immigrants_2017_2022_average.items():
            immigration_proportions_with_citizenship[(sex, age, citizenship)] = sex_age_proportion * citizenship_proportion

    initial_ed_populations = {}
    for region in tqdm(regions, desc="Regional International Emigrants"):
        regions_eds = {ed_id: ed for ed_id, ed in eds.items() if ed.region == region}

        regions_eds_populations = {ed_id: len(ed.population) for ed_id, ed in regions_eds.items()}

        for ed_id_in_region, pop_in_region in regions_eds_populations.items():
            initial_ed_populations[ed_id_in_region] = pop_in_region

        origin_regions_whole_population = []
        for ed_id, ed_object in regions_eds.items():
            origin_regions_whole_population.extend(ed_object.population)

        # num_emigrants_from_region = round(international_emigration_proportions[region] * num_emigrants_state)
        num_emigrants_from_region = regional_num_emigrants[region]

        # cohort_populations = {}
        cohort_peoples_eds_populations = {}
        for person in origin_regions_whole_population:
            if person.age > 0:
                # if person.age > 0 and (not person.moved_to_ireland_in_last_year):  # Assume people stay for at least one year
                if 0 <= person.age <= 14:
                    age_label = "0 - 14 years"
                elif 15 <= person.age <= 24:
                    age_label = "15 - 24 years"
                elif 25 <= person.age <= 44:
                    age_label = "25 - 44 years"
                elif 45 <= person.age <= 64:
                    age_label = "45 - 64 years"
                else:  # person.age >= 65:
                    age_label = "65 years and over"

                # if (person.sex, age_label) not in cohort_peoples_eds_populations:
                #     cohort_peoples_eds_populations[(person.sex, age_label)] = {person: regions_eds_populations[person.ed]}
                # else:
                #     cohort_peoples_eds_populations[(person.sex, age_label)][person] = regions_eds_populations[person.ed]

                if (person.sex, age_label, person.citizenship) not in cohort_peoples_eds_populations:
                    cohort_peoples_eds_populations[(person.sex, age_label, person.citizenship)] = {person: regions_eds_populations[person.ed]}
                else:
                    cohort_peoples_eds_populations[(person.sex, age_label, person.citizenship)][person] = regions_eds_populations[person.ed]

        # valid_proportions = {k: v for k, v in emigration_proportions_2017_2022_average.items()
        #                      if k in cohort_peoples_eds_populations}
        valid_proportions = {k: v for k, v in emigration_proportions_with_citizenship.items()
                             if k in cohort_peoples_eds_populations}

        emigrants_cohorts = random.choices(list(valid_proportions.keys()),
                                           list(valid_proportions.values()),
                                           k=num_emigrants_from_region)

        emigrant_cohort_counter = Counter(emigrants_cohorts)

        while len(emigrant_cohort_counter) > 0:
            # (sex, age_group), num_migrants_in_cohort = random.choice(list(emigrant_cohort_counter.items()))
            (sex, age_group, citizenship), num_migrants_in_cohort = random.choice(list(emigrant_cohort_counter.items()))

            # if ((sex, age_group) not in cohort_peoples_eds_populations) or \
            #         (num_migrants_in_cohort > len(cohort_peoples_eds_populations[(sex, age_group)])):
            if ((sex, age_group, citizenship) not in cohort_peoples_eds_populations) or \
                    (num_migrants_in_cohort > len(cohort_peoples_eds_populations[(sex, age_group, citizenship)])):
                # if (sex, age_group) not in cohort_peoples_eds_populations:
                if (sex, age_group, citizenship) not in cohort_peoples_eds_populations:
                    num_replacements = num_migrants_in_cohort
                    chosen_candidates = []

                    del emigrant_cohort_counter[(sex, age_group, citizenship)]
                else:
                    # num_replacements = num_migrants_in_cohort - len(cohort_peoples_eds_populations[(sex, age_group)])
                    # chosen_candidates = list(cohort_peoples_eds_populations[(sex, age_group)].keys())
                    num_replacements = num_migrants_in_cohort - len(cohort_peoples_eds_populations[(sex, age_group, citizenship)])
                    chosen_candidates = list(cohort_peoples_eds_populations[(sex, age_group, citizenship)].keys())

                    # emigrant_cohort_counter[(sex, age_group)] -= num_replacements
                    emigrant_cohort_counter[(sex, age_group, citizenship)] -= num_replacements

                if num_replacements > 0:
                    # valid_proportions = {k: v for k, v in emigration_proportions_2017_2022_average.items()
                    #                      if (k in cohort_peoples_eds_populations) and (k != (sex, age_group))}
                    valid_replacement_proportions = {k: v for k, v in emigration_proportions_with_citizenship.items()
                                                     if (k in cohort_peoples_eds_populations) and (k != (sex, age_group, citizenship))}

                    replacement_cohorts = random.choices(list(valid_replacement_proportions.keys()),
                                                         list(valid_replacement_proportions.values()),
                                                         k=num_replacements)

                    # for (replacement_sex, replacement_age_group) in replacement_cohorts:
                    #     if (replacement_sex, replacement_age_group) in emigrant_cohort_counter:
                    #         emigrant_cohort_counter[(replacement_sex, replacement_age_group)] += 1
                    #     else:
                    #         emigrant_cohort_counter[(replacement_sex, replacement_age_group)] = 1
                    for (replacement_sex, replacement_age_group, replacement_citizenship) in replacement_cohorts:
                        if (replacement_sex, replacement_age_group, replacement_citizenship) in emigrant_cohort_counter:
                            emigrant_cohort_counter[(replacement_sex, replacement_age_group, replacement_citizenship)] += 1
                        else:
                            emigrant_cohort_counter[(replacement_sex, replacement_age_group, replacement_citizenship)] = 1
            else:
                # total_pops_of_cohort = sum(list(cohort_peoples_eds_populations[(sex, age_group)].values()))
                # normalised_cohort_peoples_eds_populations = {k: v / total_pops_of_cohort for k, v in
                #                                              cohort_peoples_eds_populations[(sex, age_group)].items()}
                total_pops_of_cohort = sum(list(cohort_peoples_eds_populations[(sex, age_group, citizenship)].values()))
                normalised_cohort_peoples_eds_populations = {k: v / total_pops_of_cohort for k, v in
                                                             cohort_peoples_eds_populations[(sex, age_group, citizenship)].items()}
                chosen_candidates = np.random.choice(list(normalised_cohort_peoples_eds_populations.keys()),
                                                     size=num_migrants_in_cohort,
                                                     replace=False,
                                                     p=list(normalised_cohort_peoples_eds_populations.values()))

            for chosen_candidate in chosen_candidates:
                # del cohort_peoples_eds_populations[(sex, age_group)][chosen_candidate]
                del cohort_peoples_eds_populations[(sex, age_group, citizenship)][chosen_candidate]

                # if (sex, age_group) in state_emigrant_cohort_counts:
                #     state_emigrant_cohort_counts[(sex, age_group)] += 1
                # else:
                #     state_emigrant_cohort_counts[(sex, age_group)] = 1
                if (sex, age_group, citizenship) in state_emigrant_cohort_counts:
                    state_emigrant_cohort_counts[(sex, age_group, citizenship)] += 1
                else:
                    state_emigrant_cohort_counts[(sex, age_group, citizenship)] = 1

                # Remove them from their origin ED
                eds[chosen_candidate.ed].population.remove(chosen_candidate)
                chosen_candidate.remove_references_to_and_from_person(emigrate=True)

                # if len(cohort_peoples_eds_populations[(sex, age_group)]) == 0:
                #     del cohort_peoples_eds_populations[(sex, age_group)]
                #     del valid_proportions[(sex, age_group)]
                #
                # emigrant_cohort_counter[(sex, age_group)] -= 1
                # if emigrant_cohort_counter[(sex, age_group)] == 0:
                #     del emigrant_cohort_counter[(sex, age_group)]

                if len(cohort_peoples_eds_populations[(sex, age_group, citizenship)]) == 0:
                    del cohort_peoples_eds_populations[(sex, age_group, citizenship)]
                    # try:
                    #     del valid_proportions[(sex, age_group, citizenship)]
                    # except KeyError:
                    #     print("Got that key error on del valid proportions")

                emigrant_cohort_counter[(sex, age_group, citizenship)] -= 1
                if emigrant_cohort_counter[(sex, age_group, citizenship)] == 0:
                    del emigrant_cohort_counter[(sex, age_group, citizenship)]

    state_total_emigrants = sum(list(state_emigrant_cohort_counts.values()))
    print(f"\n{current_year} state emigrant proportions:")
    for cohort_label, count in state_emigrant_cohort_counts.items():
        print(f"\t{cohort_label}: {count / state_total_emigrants:.3f}")

    # pre_immigration_population = []
    state_immigrant_cohort_counts = {}
    # Immigration done all in one
    international_immigrants = []

    # recent_immigrant_pre_immigration_population = []
    for ed_id, ed_object in eds.items():
        for person in ed_object.population:
            if person.moved_to_ireland_in_last_year:
                # recent_immigrant_pre_immigration_population.append(person)
                person.moved_to_ireland_in_last_year = False
        # pre_immigration_population.extend(ed_object.population)

    # print(f"Number of recent immigrants: {len(recent_immigrant_pre_immigration_population)}")

    # Do this before emigration to ensure that all of the recent immigrants' characteristics are
    # captured even if they emigrate
    # pre_immigration_cohort_populations = {}
    # recent_immigrant_pre_immigration_cohort_populations = {}
    # # for person in pre_immigration_population:
    # # for person in recent_immigrant_pre_immigration_population:
    # for person in recent_immigrants_from_2022_census:
    #     # if person.age > 0:
    #     # if (person.age > 0) and person.moved_to_ireland_in_last_year:
    #     if person.age > 0:
    #         if 0 <= person.age <= 14:
    #             age_label = "0 - 14 years"
    #         elif 15 <= person.age <= 24:
    #             age_label = "15 - 24 years"
    #         elif 25 <= person.age <= 44:
    #             age_label = "25 - 44 years"
    #         elif 45 <= person.age <= 64:
    #             age_label = "45 - 64 years"
    #         else:  # person.age >= 65:
    #             age_label = "65 years and over"
    #
    #         # if (person.sex, age_label) not in pre_immigration_cohort_populations:
    #         #     pre_immigration_cohort_populations[(person.sex, age_label)] = [person]
    #         # else:
    #         #     pre_immigration_cohort_populations[(person.sex, age_label)].append(person)
    #
    #         if (person.sex, age_label, person.citizenship) not in recent_immigrant_pre_immigration_cohort_populations:
    #             recent_immigrant_pre_immigration_cohort_populations[(person.sex, age_label, person.citizenship)] = [person]
    #         else:
    #             recent_immigrant_pre_immigration_cohort_populations[(person.sex, age_label, person.citizenship)].append(person)

    # for (sex, age_group), proportion in tqdm(immigration_proportions_2017_2022_average.items(),
    #                                          desc=f"Generating international immigrants in cohort"):
    for (sex, age_group, citizenship), proportion in tqdm(immigration_proportions_with_citizenship.items(),
                                                          desc=f"Generating international immigrants in cohort"):

        num_immigrants_in_bracket = round(num_immigrants_state * proportion)

        # pre_immigration_cohort = pre_immigration_cohort_populations[(sex, age_group)]
        # pre_immigration_cohort = pre_immigration_cohort_populations[(sex, age_group, citizenship)]
        try:
            recent_immigrant_pre_immigration_cohort = recent_immigrant_pre_immigration_cohort_populations[(sex, age_group, citizenship)]
        except KeyError:  # Sex, age group, citizenship not in recent immigrants
            # Swap to a different citizenship
            # For people who aren't in the dictionary, assume citizenship is the problem
            print("Somehow didn't find the right cohort")
            possible_citizenships = list(citizenship_of_international_immigrants_2017_2022_average.keys())
            random.shuffle(possible_citizenships)
            for other_citizenship in possible_citizenships:
                if other_citizenship != citizenship:
                    possible_new_key = (sex, age_group, other_citizenship)
                    if possible_new_key in recent_immigrant_pre_immigration_cohort_populations:
                        recent_immigrant_pre_immigration_cohort = recent_immigrant_pre_immigration_cohort_populations[possible_new_key]

                        # No need to look at other citizenships, this one worked
                        break
                    elif other_citizenship == possible_citizenships[-1]:
                        # If we reached here, no citizenships worked
                        raise KeyError(f"None of the possible citizenships worked for {(sex, age_group)}")

        # if (sex, age_group) in state_immigrant_cohort_counts:
        #     state_immigrant_cohort_counts[(sex, age_group)] += num_immigrants_in_bracket
        # else:
        #     state_immigrant_cohort_counts[(sex, age_group)] = num_immigrants_in_bracket
        if (sex, age_group, citizenship) in state_immigrant_cohort_counts:
            state_immigrant_cohort_counts[(sex, age_group, citizenship)] += num_immigrants_in_bracket
        else:
            state_immigrant_cohort_counts[(sex, age_group, citizenship)] = num_immigrants_in_bracket

        international_immigrants.extend(
            create_realistic_immigrant_from_same_cohort(recent_immigrant_pre_immigration_cohort,
                                                        num_immigrants_in_bracket,
                                                        current_year=current_year))
    distribute_international_immigrants_to_eds(international_immigrants, eds)

    state_total_immigrants = sum(list(state_immigrant_cohort_counts.values()))
    print(f"\n{current_year} state immigrant proportions:")
    for cohort_label, count in state_immigrant_cohort_counts.items():
        print(f"\t{cohort_label}: {count / state_total_immigrants:.3f}")

    for ed_id, ed in eds.items():
        regional_net_international_migration[ed_id] = len(eds[ed_id].population) - initial_ed_populations[ed_id]

    return regional_net_international_migration


def create_realistic_immigrant_from_same_cohort(pre_immigration_cohort: [Individual],
                                                    num_immigrants: int,
                                                    current_year: int):

    donors = random.choices(pre_immigration_cohort, k=num_immigrants)

    # Do donor method
    immigrants = []
    for immigrant_idx in range(num_immigrants):

        immigrants.append(Individual(age=donors[immigrant_idx].age,
                                     sex=donors[immigrant_idx].sex,
                                     marital_status=donors[immigrant_idx].marital_status,
                                     citizenship=donors[immigrant_idx].citizenship,
                                     moved_to_ireland_in_last_year=True,
                                     economic_status=donors[immigrant_idx].economic_status,
                                     education=donors[immigrant_idx].education,
                                     current_year=current_year
                                     ))

    return immigrants
