import os
import random
from constants import counties_ed_ids_stripped_no_repeats, regions_counties, \
    mothers_age_and_within_marriage_births_proportions
from individual import Individual
import place_v2
from tqdm import tqdm


def regional_births(places: dict[str, place_v2.Place], year: int, f2_fertility_rates: dict[str, dict[str, float]]):
    """
    This function:
    - Decides which Individuals will have children in this year of the simulation based on their age
      group, region, and marital status
    - Creates newborns (age=0, random sex, single marital status, Irish citizenship and an economic status and education
      of 'NA')
    - Assigns the child's parent(s) as their parents and the parents' child as their child
    - Adds the newborn to the mother's ED's population

    :param places: A dictionary of EDs with ED_IDs being the keys, and their Place objects being the values
    :param year:The current year of the simulation
    :param f2_fertility_rates: Per-region, per-age group fertility rates
    :return: a dictionary of the number of births in each ED
    """

    num_births_per_ed = {}

    for region, constituent_counties in regions_counties.items():

        regions_pop = []
        for county in constituent_counties:
            for ed_id in counties_ed_ids_stripped_no_repeats[county]:
                regions_pop.extend(places[ed_id].population)

        women_in_age_bands = {
            "15 - 19 years": 0,
            "20 - 24 years": 0,
            "25 - 29 years": 0,
            "30 - 34 years": 0,
            "35 - 39 years": 0,
            "40 - 44 years": 0,
            "45 - 49 years": 0
        }

        for person in regions_pop:
            if person.sex == "F":
                if 15 <= person.age <= 19:
                    women_in_age_bands["15 - 19 years"] += 1
                elif 20 <= person.age <= 24:
                    women_in_age_bands["20 - 24 years"] += 1
                elif 25 <= person.age <= 29:
                    women_in_age_bands["25 - 29 years"] += 1
                elif 30 <= person.age <= 34:
                    women_in_age_bands["30 - 34 years"] += 1
                elif 35 <= person.age <= 39:
                    women_in_age_bands["35 - 39 years"] += 1
                elif 40 <= person.age <= 44:
                    women_in_age_bands["40 - 44 years"] += 1
                elif 45 <= person.age <= 49:
                    women_in_age_bands["45 - 49 years"] += 1

        male_counter = 0
        female_counter = 0

        for age_group, num_women_in_age_bracket in women_in_age_bands.items():
            num_births_to_this_age_bracket = num_women_in_age_bracket / 1000 * f2_fertility_rates[region][age_group]
            lower_age = int(age_group.split(" ")[0])
            upper_age = int(age_group.split(" ")[2])
            # Find eligible mothers
            women_in_age_bracket = list(
                filter(lambda potential_mother: (potential_mother.sex == "F") and (
                        lower_age <= potential_mother.age <= upper_age),
                       regions_pop))

            # TODO: Refactor
            if lower_age >= 25:
                # Married = true, not married = False
                women_in_age_bracket_within_marriage = {True: [], False: []}
                for woman in women_in_age_bracket:
                    if woman.marital_status == "MAR":
                        women_in_age_bracket_within_marriage[True].append(woman)
                    else:
                        women_in_age_bracket_within_marriage[False].append(woman)

                for married, women_with_marital_status in women_in_age_bracket_within_marriage.items():
                    if married:
                        num_births_to_women_with_marital_status = round(num_births_to_this_age_bracket *
                                                                        mothers_age_and_within_marriage_births_proportions[
                                                                            age_group])
                    else:
                        num_births_to_women_with_marital_status = \
                            round(num_births_to_this_age_bracket *
                                  (1 - mothers_age_and_within_marriage_births_proportions[age_group]))

                    print(f"Region: {region}")
                    print(f"Num births to {'married' if married else 'unmarried'} women: {num_births_to_women_with_marital_status}")
                    print(f"Num {'married' if married else 'unmarried'} women in {age_group}: {len(women_with_marital_status)}")

                    mother_will_have_next_birth_too = False
                    if num_births_to_women_with_marital_status > 0:
                        for num_babies_born in range(num_births_to_women_with_marital_status):
                            if not mother_will_have_next_birth_too:
                                # Last turn's mother wasn't assigned to be the mother of this child too
                                # Mother to last birth in the mother's cohort can't be chosen to have another baby for
                                #   the next birth because there is no next birth

                                # Randomly choose a fitting mother
                                mother = random.choice(women_with_marital_status)
                                if (random.uniform(0, 1) < 0.018) and \
                                        (num_babies_born != num_births_to_women_with_marital_status - 1):
                                    mother_will_have_next_birth_too = True
                            else:
                                # Same mother as last turn will have this birth
                                # We'll remove her as a possible mother again then
                                mother_will_have_next_birth_too = False

                            # Find parents if they're married
                            parents = [mother]
                            if (hasattr(mother, 'spouse')) and (mother.spouse != "Outsider"):
                                parents.append(mother.spouse)

                            # Add a baby
                            newborn = Individual(age=0, sex=random.choice(["F", "M"]), marital_status="SGL", citizenship="IE", economic_status="NA", education="NA",
                                                 parents=parents, ed=mother.ed, born_in_simulation=True, current_year=year)

                            places[mother.ed].population.append(newborn)

                            if mother.ed in num_births_per_ed:
                                num_births_per_ed[mother.ed] += 1
                            else:
                                num_births_per_ed[mother.ed] = 1

                            for parent in parents:
                                if hasattr(parent, 'children'):
                                    parent.children.append(newborn)
                                else:
                                    parent.children = [newborn]

                            if newborn.sex == "M":
                                male_counter += 1
                            else:
                                female_counter += 1

                            if not mother_will_have_next_birth_too:
                                women_with_marital_status.remove(mother)
            else:
                mother_will_have_next_birth_too = False
                for num_babies_born in range(round(num_births_to_this_age_bracket)):
                    if not mother_will_have_next_birth_too:
                        # Last turn's mother wasn't assigned to be the mother of this child too
                        # Mother to last birth in the mother's cohort can't be chosen to have another baby for
                        #   the next birth because there is no next birth

                        # Randomly choose a fitting mother
                        mother = random.choice(women_in_age_bracket)
                        if (random.uniform(0, 1) < 0.018) and \
                                (num_babies_born != num_births_to_this_age_bracket - 1):
                            mother_will_have_next_birth_too = True
                    else:
                        # Same mother as last turn will have this birth
                        # We'll remove her as a possible mother again then
                        mother_will_have_next_birth_too = False

                    # Find parents if they're married
                    parents = [mother]
                    if (hasattr(mother, 'spouse')) and (mother.spouse != "Outsider"):
                        parents.append(mother.spouse)

                    # Add a baby
                    newborn = Individual(age=0, sex=random.choice(["F", "M"]), marital_status="SGL", economic_status="NA", education="NA",
                                         parents=parents, ed=mother.ed, born_in_simulation=True, current_year=year)

                    places[mother.ed].population.append(newborn)

                    if mother.ed in num_births_per_ed:
                        num_births_per_ed[mother.ed] += 1
                    else:
                        num_births_per_ed[mother.ed] = 1

                    for parent in parents:
                        if hasattr(parent, 'children'):
                            parent.children.append(newborn)
                        else:
                            parent.children = [newborn]

                    if newborn.sex == "M":
                        male_counter += 1
                    else:
                        female_counter += 1

                    if not mother_will_have_next_birth_too:
                        women_in_age_bracket.remove(mother)

    return num_births_per_ed


if __name__ == '__main__':
    start_year = 2022
    static_generation_approach = "ipf"

    population_folder = f"./populations/{static_generation_approach}/"
    areas_of_interest = [f.split(".")[0] for f in os.listdir(population_folder)]

    num_women_between_20_and_40 = 0

    places = {}
    for area in tqdm(areas_of_interest, desc="Population Initialisation"):
        for county, constituent_eds_ids in counties_ed_ids_stripped_no_repeats.items():
            if area in constituent_eds_ids:
                areas_county = county
                break

        for higher_region, constituent_counties in regions_counties.items():
            if areas_county in constituent_counties:
                areas_region = higher_region
                break

        places[area] = place_v2.Place(ed_id=area, county=areas_county, region=areas_region,
                             static_generation_approach=static_generation_approach)

        num_women_between_20_and_40 += len([person for person in places[area].population if
                                            person.sex == "F" and 20 <= person.age <= 40])

    print(num_women_between_20_and_40)

