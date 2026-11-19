import random
import math
import numpy as np

from constants import regions_counties, education_to_number, counties_ed_ids_stripped_no_repeats, \
    same_sex_marriage_age_proportions, opposite_sex_marriage_age_proportions, divorce_rate, separation_rate
from individual import Individual
from tqdm import tqdm


def annual_relationship_loop(places):
    """
    Calls the separation function, and then calls the functions to match up unmarried people on a region-by-region basis

    :param places: A dictionary of EDs with ED_IDs being the keys, and their Place objects being the values
    """

    whole_population = []
    for _, place in places.items():
        whole_population.extend(place.population)

    # Break up some existing marriages
    married_people = [person for person in whole_population if person.marital_status == "MAR"]

    separate_marriages_v2(married_people)

    # Create new marriages (by region)
    for region, constituent_counties in regions_counties.items():
        regions_pop = []
        for county in constituent_counties:
            for ed_id in counties_ed_ids_stripped_no_repeats[county]:
                if ed_id in places:  # TODO: Remove this for full simulations
                    regions_pop.extend(places[ed_id].population)

        print("- Marrying those who are already married but do not have a spouse")
        married_pop_without_spouses_in_region = list(filter(lambda person: (person.marital_status == "MAR")
                                                           and (not hasattr(person, "spouse")),
                                            regions_pop))

        match_couples_to_be_married_in_region_no_specified_sexualities(married_pop_without_spouses_in_region)
        print(f"- Marriages completed in {region}\n")

        unmarried_adults_in_region = [person for person in regions_pop if
                                      (person.marital_status != "MAR") and (person.age >= 15)]

        # https://www.cso.ie/en/releasesandpublications/ep/p-mar/marriages2023/mainresults/
        new_marriage_rate = 4.0
        # Marriage rate is based on size of whole population. 2 people per marriage
        num_people_to_get_married = round(new_marriage_rate * (len(regions_pop) / 1000) * 2)
        marry_unmarried_people_in_region(unmarried_adults_in_region, num_people_to_get_married=num_people_to_get_married)


def separate_marriages_v2(married_people: [Individual]):
    """
    Calculates the number of divorces and separations to happen among the married population and separates that amount
    of couples

    :param married_people: A list of Individuals with the marital status 'MAR'
    """

    num_divorces = round(divorce_rate * len(married_people))
    if not num_divorces % 2 == 0:
        num_divorces -= 1  # Must be even
    num_separations = round(separation_rate * len(married_people))
    if not num_separations % 2 == 0:
        num_separations -= 1  # Must be even

    completed_separations = 0
    pbar = tqdm(num_separations + num_divorces, desc="Completed Separations")
    while completed_separations < num_separations + num_divorces:
        person = married_people.pop(random.randrange(len(married_people)))
        if person.marital_status == "MAR":  # Not already divorced
            pbar.update(1)
            completed_separations += 1
            person.marital_status = "SEP"
            if hasattr(person, 'spouse') and person.spouse != "Outsider":
                person.spouse.marital_status = "SEP"
                try:
                    del person.spouse.spouse
                except AttributeError:
                    print("Spouse already deleted")
                del person.spouse

    pbar.close()


def marry_unmarried_people_in_region(unmarried_adults_in_region: [Individual], num_people_to_get_married: int):
    """
    Decides which unmarried Individuals are to be married this year and then calls a function that matches Individuals
    into couples (both same- and opposite-sex)

    :param unmarried_adults_in_region: Individuals with a marital status other than 'MAR' in a region
    :param num_people_to_get_married: The number of people to get married in the region (based on marriage rate)
    :return:
    """
    same_sex_marriage_rate = 0.03  # 3 percent of marriages are same sex

    people_to_be_married_to_same_sex = {"M": [], "F": []}
    people_to_be_married_to_opposite_sex = {"M": [], "F": []}

    for sex, age_groups_proportions in same_sex_marriage_age_proportions.items():
        # We assume there are approximately the same number of same sex marriages for both sexes
        sexes_number_of_people_to_marry_same_sex = num_people_to_get_married * (same_sex_marriage_rate / 2)
        sexes_number_of_people_to_marry_opposite_sex = num_people_to_get_married * ((1-same_sex_marriage_rate) / 2)
        for age_group, same_sex_proportion in age_groups_proportions.items():
            num_people_in_age_bracket_to_get_married_to_same_sex = \
                round(sexes_number_of_people_to_marry_same_sex * same_sex_proportion)
            num_people_in_age_bracket_to_get_married_to_opposite_sex = \
                round(sexes_number_of_people_to_marry_opposite_sex * opposite_sex_marriage_age_proportions[sex][age_group])

            if age_group != "GE_60":
                age_group_lower_bound = int(age_group.split("_")[0])
                age_group_upper_bound = int(age_group.split("_")[1])
            else:
                age_group_lower_bound = 60
                age_group_upper_bound = np.inf

            people_in_sex_and_age_bracket = [person for person in unmarried_adults_in_region if (person.sex == sex) and
                                             (age_group_lower_bound <= person.age <= age_group_upper_bound)]

            if num_people_in_age_bracket_to_get_married_to_same_sex > 0:
                for _ in range(num_people_in_age_bracket_to_get_married_to_same_sex):
                    people_to_be_married_to_same_sex[sex].append(
                        people_in_sex_and_age_bracket.pop(random.randrange(len(people_in_sex_and_age_bracket))))

            if num_people_in_age_bracket_to_get_married_to_opposite_sex > 0:
                for _ in range(num_people_in_age_bracket_to_get_married_to_opposite_sex):
                    people_to_be_married_to_opposite_sex[sex].append(
                        people_in_sex_and_age_bracket.pop(random.randrange(len(people_in_sex_and_age_bracket))))

    match_couples_to_be_married_in_region_with_specified_sexualities(same_sex_spouses=people_to_be_married_to_same_sex,
                                                                     opposite_sex_spouses=people_to_be_married_to_opposite_sex)


def match_person_to_partner(person: Individual, possible_partners: [Individual]):
    """
    Performs a weighted random choice a partner for an Individual from a list of potential partners based on their
    similarity in terms of age and education level

    :param person:
    :param possible_partners:
    :return:
    """
    dissimilarities = [(rank_dissimilarity_2(person, partner), partner) for partner in possible_partners]

    partners_sorted_by_dissimilarity = sorted(dissimilarities, key=lambda x: x[0], reverse=True)

    number_of_possible_spouses = len(dissimilarities)

    dirichlet2 = np.random.dirichlet(np.ones(number_of_possible_spouses)/20, size=1)
    sorted_dirichlet = np.sort(dirichlet2).tolist()[0]

    # Sample partner obeying homogamy
    _, partner = random.choices(partners_sorted_by_dissimilarity, weights=sorted_dirichlet, k=1)[0]

    # Make each person the other person's spouse
    person.spouse = partner
    partner.spouse = person

    # Make each person married
    person.marital_status = "MAR"
    partner.marital_status = "MAR"

    return partner


def rank_dissimilarity_2(person_1: Individual, person_2: Individual):
    """
    Calculates a numerical measure of dissimilarity between two individuals based on their ages and educations

    :param person_1:
    :param person_2:
    :return: The Manhattan distance between the Individuals
    """
    if (person_1.education in ["NS", "NA"]) or (person_2.education in ["NS", "NA"]):
        return abs(person_1.age - person_2.age)
    else:
        return abs(person_1.age - person_2.age) + abs(education_to_number[person_1.education] - education_to_number[person_2.education])


def rank_dissimilarity(person_1_age_and_education: (), person_2_age_and_education: ()):
    """
    Calculates a numerical measure of dissimilarity between two individuals based on their ages and educations

    :param person_1_age_and_education: As a tuple
    :param person_2_age_and_education: As a tuple
    :return: The Manhattan distance between the Individuals
    """

    # No education
    if (not person_1_age_and_education[1]) or (not person_2_age_and_education[1]):
        return abs(person_1_age_and_education[0] - person_2_age_and_education[0])
    else:
        return abs(person_1_age_and_education[0] - person_2_age_and_education[0]) + abs(person_1_age_and_education[1] -
                                                                                        person_2_age_and_education[1])


# Input: Married people
# People are matched based on age and education level
def match_couples_to_be_married_in_region_no_specified_sexualities(people_to_marry: [Individual],
                                                                   marry_to_outsiders=True,
                                                                   verbose=True):
    """
    Matches individuals who have previously been assigned a marital status of 'MAR', e.g. from the static
    microsimulation process, but who do not have a spouse.

    :param people_to_marry: List of Individuals to be married
    :param marry_to_outsiders: A Boolean which decides whether 'leftover' individuals are assigned a spouse of
    'Outsider' or not
    :param verbose:
    """

    # https://data.cso.ie/table/VSB02 & https://data.cso.ie/table/VSA44
    homosexual_proportion = 0.03

    all_married_females = list(filter(lambda person: person.sex == "F", people_to_marry))
    min_number_homosexual_females = math.floor(len(all_married_females) * homosexual_proportion)
    if min_number_homosexual_females % 2 == 0:  # Even number
        homosexual_married_females = [all_married_females.pop(random.randrange(len(all_married_females))) for _ in
                                      range(min_number_homosexual_females)]
    else:
        homosexual_married_females = [all_married_females.pop(random.randrange(len(all_married_females))) for _ in
                                      range(min_number_homosexual_females + 1)]
    heterosexual_married_females = all_married_females.copy()
    random.shuffle(heterosexual_married_females)

    all_married_males = list(filter(lambda person: person.sex == "M", people_to_marry))
    min_number_homosexual_males = math.floor(len(all_married_males) * homosexual_proportion)
    if min_number_homosexual_males % 2 == 0:  # Even number
        homosexual_married_males = [all_married_males.pop(random.randrange(len(all_married_males))) for _ in
                                      range(min_number_homosexual_males)]
    else:
        homosexual_married_males = [all_married_males.pop(random.randrange(len(all_married_males))) for _ in
                                    range(min_number_homosexual_males+1)]
    heterosexual_married_males = all_married_males.copy()
    random.shuffle(heterosexual_married_males)

    print(f"Num married women: {len(heterosexual_married_females)}")
    print(f"Num married men: {len(heterosexual_married_males)}")

    females_minus_males = len(heterosexual_married_females) - len(heterosexual_married_males)
    if females_minus_males > 0:  # More females than males
        for _ in range(females_minus_males):
            wife = heterosexual_married_females.pop()
            if marry_to_outsiders:
                wife.spouse = "Outsider"
    elif females_minus_males < 0:  # More males than females
        for _ in range(abs(females_minus_males)):
            husband = heterosexual_married_males.pop()
            if marry_to_outsiders:
                husband.spouse = "Outsider"

    heterosexual_married_females_stats = [
        (f.age, education_to_number[f.education]) if f.education not in ["NS", "NA"] else (f.age, random.randint(0,8))
        for f in heterosexual_married_females]

    heterosexual_married_males_stats = [
        (m.age, education_to_number[m.education]) if m.education not in ["NS", "NA"] else (m.age, random.randint(0,8))
        for m in heterosexual_married_males]

    dissimilarities = ([rank_dissimilarity(wifes_stats, potential_husbands_stats)
                        for potential_husbands_stats in heterosexual_married_males_stats]
                       for wifes_stats in heterosexual_married_females_stats)

    for wifes_idx, wifes_dissimilarities in (
        tqdm(enumerate(dissimilarities), desc="Evaluating potential marriage partners") if verbose else enumerate(
            dissimilarities)):
        num_spouses_to_consider = 20 if 20 < len(heterosexual_married_males) else len(heterosexual_married_males)

        # Get 20 closest spouses
        top_n_spouses = sorted(range(len(wifes_dissimilarities)), key=lambda i: wifes_dissimilarities[i])[:num_spouses_to_consider]

        # Sample one according to dirichlet
        dirichlet2 = np.random.dirichlet(np.ones(num_spouses_to_consider)/20, size=1)
        sorted_dirichlet = (- np.sort(- dirichlet2)).tolist()[0]  # Sort in descending order

        # Sample partner obeying homogamy
        partners_idx = random.choices(top_n_spouses, weights=sorted_dirichlet, k=1)[0]

        partner = heterosexual_married_males[partners_idx]

        person = heterosexual_married_females[wifes_idx]

        # Make each person the other person's spouse
        person.spouse = partner
        partner.spouse = person

        # Make each person married (even if they already are)
        person.marital_status = "MAR"
        partner.marital_status = "MAR"

        # Make all spouse's other distances infinity
        heterosexual_married_males_stats.pop(partners_idx)
        heterosexual_married_males.pop(partners_idx)

    # Female marriages
    while len(homosexual_married_females) > 0:
        # Pick last woman
        wife_1 = homosexual_married_females.pop()

        wife_2 = match_person_to_partner(wife_1, homosexual_married_females)
        homosexual_married_females.remove(wife_2)

    # Male marriages
    while len(homosexual_married_males) > 0:
        # Pick last man
        husband_1 = homosexual_married_males.pop()

        husband_2 = match_person_to_partner(husband_1, homosexual_married_males)
        homosexual_married_males.remove(husband_2)


# Input: Lists of spouses separated by sexuality
def match_couples_to_be_married_in_region_with_specified_sexualities(same_sex_spouses: dict[str, list],
                                                                     opposite_sex_spouses: dict[str, list]):
    """
    Matches individuals who will be assigned a marital status of 'MAR' and assigns them a 'spouse' characteristic

    :param same_sex_spouses: A dictionary of both males and females to be married to the same sex
    :param opposite_sex_spouses: A dictionary of both males and females to be married to the opposite sex
    """
    homosexual_married_females = same_sex_spouses["F"]
    heterosexual_married_females = opposite_sex_spouses["F"]

    homosexual_married_males = same_sex_spouses["M"]
    heterosexual_married_males = opposite_sex_spouses["M"]

    random.shuffle(homosexual_married_females)
    random.shuffle(heterosexual_married_females)

    random.shuffle(homosexual_married_males)
    random.shuffle(heterosexual_married_males)

    print(f"\t\t- Num women to be married to men: {len(heterosexual_married_females)}")
    print(f"\t\t- Num men to be married to women: {len(heterosexual_married_males)}")

    females_minus_males_heterosexual = len(heterosexual_married_females) - len(heterosexual_married_males)
    if females_minus_males_heterosexual > 0:  # More females than males
        for _ in range(females_minus_males_heterosexual):
            wife = heterosexual_married_females.pop()
            wife.spouse = "Outsider"
    elif females_minus_males_heterosexual < 0:  # More males than females
        for _ in range(abs(females_minus_males_heterosexual)):
            husband = heterosexual_married_males.pop()
            husband.spouse = "Outsider"

    if len(homosexual_married_females) % 2 != 0:
        # Remove one to make it even
        wife = homosexual_married_females.pop()
        wife.spouse = "Outsider"

    if len(homosexual_married_males) % 2 != 0:
        # Remove one to make it even
        husband = homosexual_married_males.pop()
        husband.spouse = "Outsider"

    heterosexual_married_females_stats = [
        (f.age, education_to_number[f.education]) if f.education not in ["NS", "NA"] else (f.age, random.randint(0,8))
        for f in heterosexual_married_females]

    heterosexual_married_males_stats = [
        (m.age, education_to_number[m.education]) if m.education not in ["NS", "NA"] else (m.age, random.randint(0,8))
        for m in heterosexual_married_males]

    dissimilarities = ([rank_dissimilarity(wifes_stats, potential_husbands_stats)
                        for potential_husbands_stats in heterosexual_married_males_stats]
                       for wifes_stats in heterosexual_married_females_stats)

    for wifes_idx, wifes_dissimilarities in tqdm(enumerate(dissimilarities), desc="Evaluating potential marriage partners"):
        num_spouses_to_consider = 20 if 20 < len(heterosexual_married_males) else len(heterosexual_married_males)
        # Get 20 closest spouses
        top_n_spouses = sorted(range(len(wifes_dissimilarities)), key=lambda i: wifes_dissimilarities[i])[:num_spouses_to_consider]

        # Sample one according to dirichlet
        dirichlet2 = np.random.dirichlet(np.ones(num_spouses_to_consider)/20, size=1)
        sorted_dirichlet = (- np.sort(- dirichlet2)).tolist()[0]  # Sort in descending order

        # Sample partner obeying homogamy
        partners_idx = random.choices(top_n_spouses, weights=sorted_dirichlet, k=1)[0]

        partner = heterosexual_married_males[partners_idx]

        person = heterosexual_married_females[wifes_idx]

        # Make each person the other person's spouse
        person.spouse = partner
        partner.spouse = person

        # Make each person married
        person.marital_status = "MAR"
        partner.marital_status = "MAR"

        # Make all spouse's other distances infinity
        heterosexual_married_males_stats.pop(partners_idx)
        heterosexual_married_males.pop(partners_idx)

    # Female same sex marriages
    while len(homosexual_married_females) > 0:
        # Pick last woman
        wife_1 = homosexual_married_females.pop()

        wife_2 = match_person_to_partner(wife_1, homosexual_married_females)
        homosexual_married_females.remove(wife_2)

    # Male same sex marriages
    while len(homosexual_married_males) > 0:
        # Pick last man
        husband_1 = homosexual_married_males.pop()

        husband_2 = match_person_to_partner(husband_1, homosexual_married_males)
        homosexual_married_males.remove(husband_2)
