import os
import random
from confidential_constants import economic_status_by_age_sex_and_education_without_students, economic_status_by_age_sex_education_and_citizenship_without_students
from constants import counties_ed_ids_stripped_no_repeats, regions_counties, \
    citizenship_of_international_emigrants_2017_2022_average
from place_v2 import Place
from tqdm import tqdm
import main_v2


def change_peoples_economic_statuses_v2(places: dict[str, Place]):
    whole_population = []
    for _, place in places.items():
        whole_population.extend(place.population)

    # Children will remain NA. Students can get sorted by the education module
    non_students_and_children = list(filter(lambda person: (person.economic_status != "S") and (person.age >= 15),
                                            whole_population))

    age_ranges = []
    for (age_range, _, _) in economic_status_by_age_sex_and_education_without_students.keys():
        if age_range not in age_ranges:
            age_ranges.append(age_range)

    pbar = tqdm(total=len(non_students_and_children), desc="Bracketing adults by age, sex and education")

    people_in_population_with_age_sex_and_education = {}
    while len(non_students_and_children) > 0:
        pbar.update(1)
        person = non_students_and_children.pop()

        # Find person's bracket
        for age_range in age_ranges:
            if age_range != "GE_85":
                age_range_lower_bound = int(age_range.split("_")[0])
                age_range_upper_bound = int(age_range.split("_")[1])
            else:
                age_range_lower_bound = 85
                age_range_upper_bound = 200

            if age_range_lower_bound <= person.age <= age_range_upper_bound:
                key = (age_range, person.sex, person.education)
                if key in people_in_population_with_age_sex_and_education:
                    people_in_population_with_age_sex_and_education[key].append(person)
                    break
                else:
                    people_in_population_with_age_sex_and_education[key] = [person]

    pbar.close()

    for bracket_key, people_in_bracket in tqdm(people_in_population_with_age_sex_and_education.items(),
                                               desc="Changing Economic Statuses for All Brackets of People"):
        num_people_in_bracket = len(people_in_bracket)

        num_brackets_not_in_it = 0
        # For people who aren't in the dictionary, don't change their economic status
        if bracket_key in economic_status_by_age_sex_and_education_without_students:
            economic_status_proportions = economic_status_by_age_sex_and_education_without_students[bracket_key]

            economic_statuses = random.choices(list(economic_status_proportions.keys()),
                                               list(economic_status_proportions.values()),
                                               k=num_people_in_bracket)

            for idx, person in enumerate(people_in_bracket):
                person.economic_status = economic_statuses[idx]
        else:
            num_brackets_not_in_it += 1


def change_peoples_economic_statuses_v3(places: dict[str, Place]):
    whole_population = []
    for _, place in places.items():
        whole_population.extend(place.population)

    # Children will remain NA. Students can get sorted by the education module
    non_students_and_children = list(filter(lambda person: (person.economic_status != "S") and (person.age >= 15),
                                            whole_population))

    age_ranges = []
    # for (age_range, _, _) in economic_status_by_age_sex_and_education_without_students.keys():
    for (age_range, _, _, _) in economic_status_by_age_sex_education_and_citizenship_without_students.keys():
        if age_range not in age_ranges:
            age_ranges.append(age_range)

    pbar = tqdm(total=len(non_students_and_children), desc="Bracketing adults by age, sex and education")

    people_in_population_with_age_sex_education_and_citizenship = {}
    while len(non_students_and_children) > 0:
        pbar.update(1)
        person = non_students_and_children.pop()

        # Find person's bracket
        for age_range in age_ranges:
            if age_range != "GE_85":
                age_range_lower_bound = int(age_range.split("_")[0])
                age_range_upper_bound = int(age_range.split("_")[1])
            else:
                age_range_lower_bound = 85
                age_range_upper_bound = 200

            if age_range_lower_bound <= person.age <= age_range_upper_bound:
                key = (age_range, person.sex, "T2_1" + person.citizenship + "C", person.education)
                if key in people_in_population_with_age_sex_education_and_citizenship:
                    people_in_population_with_age_sex_education_and_citizenship[key].append(person)
                    break
                else:
                    people_in_population_with_age_sex_education_and_citizenship[key] = [person]

    pbar.close()

    for bracket_key, people_in_bracket in tqdm(people_in_population_with_age_sex_education_and_citizenship.items(),
                                               desc="Changing Economic Statuses for All Brackets of People"):
        num_people_in_bracket = len(people_in_bracket)

        # num_brackets_not_in_it = 0
        if bracket_key in economic_status_by_age_sex_education_and_citizenship_without_students:
            economic_status_proportions = economic_status_by_age_sex_education_and_citizenship_without_students[bracket_key]

            economic_statuses = random.choices(list(economic_status_proportions.keys()),
                                               list(economic_status_proportions.values()),
                                               k=num_people_in_bracket)

            for idx, person in enumerate(people_in_bracket):
                person.economic_status = economic_statuses[idx]
        else:
            # For people who aren't in the dictionary, assume citizenship is the problem
            possible_citizenships = list(citizenship_of_international_emigrants_2017_2022_average.keys())
            random.shuffle(possible_citizenships)
            for other_citizenship in possible_citizenships:
                formatted_other_citizenship = "T2_1" + other_citizenship + "C"
                if other_citizenship != bracket_key[2]:
                    possible_new_key = list(bracket_key)
                    possible_new_key[2] = formatted_other_citizenship
                    possible_new_key = tuple(possible_new_key)
                    if possible_new_key in economic_status_by_age_sex_education_and_citizenship_without_students:
                        economic_status_proportions = economic_status_by_age_sex_education_and_citizenship_without_students[possible_new_key]

                        economic_statuses = random.choices(list(economic_status_proportions.keys()),
                                                           list(economic_status_proportions.values()),
                                                           k=num_people_in_bracket)

                        for idx, person in enumerate(people_in_bracket):
                            person.economic_status = economic_statuses[idx]

                        # No need to look at other citizenships, this one worked
                        break


if __name__ == '__main__':
    start_year = 2022
    # static_generation_approach = "ga_renamed"
    static_generation_approach = "ipf_no_zero_cells_less_iter"

    population_folder = f"./populations/{static_generation_approach}/"
    # areas_of_interest = [f.split(".")[0] for f in os.listdir(population_folder)]
    areas_of_interest = [f.split(".")[0] for f in os.listdir(population_folder) if f[-4:]==".pkl"]

    areas_to_test = random.sample(areas_of_interest, k=100)

    places = {}
    for area in tqdm(areas_to_test, desc="Population Initialisation"):
        for county, constituent_eds_ids in counties_ed_ids_stripped_no_repeats.items():
            if area in constituent_eds_ids:
                areas_county = county
                break

        for higher_region, constituent_counties in regions_counties.items():
            if areas_county in constituent_counties:
                areas_region = higher_region
                break

        places[area] = Place(ed_id=area, county=areas_county, region=areas_region, static_generation_approach=static_generation_approach)

    ireland_initial_population = []
    for _, place in places.items():
        ireland_initial_population.extend(place.population)
    main_v2.setup(ireland_initial_population, start_year, places)

    # change_peoples_economic_statuses_v2(places)
    change_peoples_economic_statuses_v3(places)