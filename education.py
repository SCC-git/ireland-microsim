import random

from tqdm import tqdm

from individual import Individual
from constants import education_to_number,  \
    broad_educations_to_specific_education_proportions,  \
    education_durations, \
    school_enrollment_age, plc_proportion, higher_cert_proportion, degree_proportion, education_dropout_rates, \
    number_to_education, regions_counties, counties_ed_ids_stripped_no_repeats,\
    parents_highest_education_to_childs_highest_education_range, \
    proportion_of_younger_adults_that_should_be_students, older_adult_educations_2022, \
    regional_adult_student_proportions_per_age_group_sexed
from place_v2 import Place

broad_educations = [2, 5, 8]


def education_loop(places: dict[str, Place], current_year: int):
    """
    This function calls each of the operating functions in the education module in the desired order and modifies the
    population(s) in-place

    :param places: A dictionary of EDs with ED_IDs being the keys, and their Place objects being the values
    :param current_year: The current year of the simulation
    """

    whole_population = []
    for _, place in places.items():
        whole_population.extend(place.population)

    valid_education_people = [person for person in whole_population if person.education not in ["NA", "NS"]]
    years_broad_educations_to_specific_education_proportions = \
        get_years_broad_educations_to_specific_education_proportions(valid_education_people)

    newborns = [person for person in whole_population if person.age==0]
    for newborn in tqdm(newborns, desc="Levels of education for newborns"):
        if hasattr(newborn, 'parents'):
            predict_newborns_highest_level_of_education(newborn,
                                                        years_broad_educations_to_specific_education_proportions)

    students = [person for person in whole_population if person.economic_status == "S"]

    students_that_arent_set_up_properly = [student for student in students if not hasattr(student, 'graduation_date')]
    estimate_level_of_education_for_students(students_that_arent_set_up_properly, current_year=current_year)

    remaining_students = dropout_students(students, current_year=current_year)

    graduate_students(remaining_students, current_year=current_year)

    # Add children of the appropriate age to school
    add_children_to_school(whole_population, current_year=current_year)

    educate_adults_more_simply(places, current_year=current_year)

    younger_adults = []
    for _, place in places.items():
        younger_adults.extend([person for person in place.population if (18 <= person.age <= 24)])
    educate_younger_adults_more_simply(younger_adults=younger_adults, current_year=current_year)


def estimate_level_of_education_for_students(students: [Individual], current_year: int):
    """
    This is a helper function which estimates (based on age) the level of education of students who have an invalid
    (or nonexistent) education for whatever reason

    :param students: List of Individuals with an economic status of 'S'
    :param current_year: The current year of the simulation
    """

    print("- Getting Education for those under 18")
    children = list(filter(lambda student: student.age < 18, students))
    get_graduation_date_for_those_already_in_school(children, current_year=current_year)

    print("- Getting Education for those between 18 and 25")
    young_adults = list(filter(lambda student: 18 <= student.age < 25, students))
    assign_education_to_young_adults(young_adults, current_year)

    print("- Getting Education for those over 25\n")
    older_students = list(filter(lambda student: student.age >= 25, students))
    assign_education_to_older_adults(older_students, current_year)


def highest_parents_highest_level_of_education(parents: [Individual]):
    """
    Calculates the highest level of education achieved by either parent

    :param parents: A list of Individuals who have been assigned as a parent to another Individual
    :return: The highest level of education achieved by either parent
    """

    parents_educations = []
    for parent in parents:
        if parent.education not in ["NA", "NS"]:
            parents_educations.append(education_to_number[parent.education])
    if len(parents_educations) > 0:
        return max(parents_educations)
    else:
        return "None valid"


def predict_newborns_highest_level_of_education(baby: Individual,
                                                years_broad_education_to_specific=broad_educations_to_specific_education_proportions):
    """
    Predicts a newborn's highest level of education they will attain in their life, based on their parents' highest
    level of education achieved and that statistic's historical data

    :param baby: The newborn Individual
    :param years_broad_education_to_specific: A dictionary specifying the proportion of individuals within each level of
     education at the primary, secondary and tertiary levels for the year
    :return: The newborn's predicted highest level of education to be attained
    """

    parents_highest = highest_parents_highest_level_of_education(baby.parents)

    if parents_highest == "None valid":
        return

    # Get relevant parent's dictionary
    for education_range, quali_dict in parents_highest_education_to_childs_highest_education_range.items():
        if parents_highest in education_range:
            education_proportions_at_parents_education_level = quali_dict
            break

    babys_broad_education = random.choices(list(education_proportions_at_parents_education_level.keys()),
                                           weights=list(education_proportions_at_parents_education_level.values()), k=1)[0]

    specific_educations_proportions = years_broad_education_to_specific[
        babys_broad_education]
    specific_education_from_broad_education = \
    random.choices(list(specific_educations_proportions.keys()), weights=list(specific_educations_proportions.values()), k=1)[0]

    baby.education_to_be_achieved_in_lifetime = specific_education_from_broad_education

    return specific_education_from_broad_education


def get_years_broad_educations_to_specific_education_proportions(population_with_valid_education: [Individual]):
    """
    Calculates the proportion of individuals within each level of education at the primary, secondary and tertiary
    levels for the current year

    :param population_with_valid_education: All Individuals with a valid education characteristic
    :return: A dictionary with the proportions within each education level
    """

    years_broad_educations_to_specific_education_counts = {2: {1: 0, 2: 0},
                                                           5: {3: 0, 4: 0, 5: 0},
                                                           8: {6: 0, 7: 0, 8: 0}}

    for person in population_with_valid_education:
        persons_education_as_number = education_to_number[person.education]
        if persons_education_as_number in range(1, 3):
            years_broad_educations_to_specific_education_counts[2][persons_education_as_number] += 1
        elif persons_education_as_number in range(3, 6):
            years_broad_educations_to_specific_education_counts[5][persons_education_as_number] += 1
        elif persons_education_as_number in range(6, 9):
            years_broad_educations_to_specific_education_counts[8][persons_education_as_number] += 1

    years_broad_educations_to_specific_education_proportions = {}
    for overall_level, levels_counts_dict in years_broad_educations_to_specific_education_counts.items():
        years_broad_educations_to_specific_education_proportions[overall_level] = {}
        total_count_of_level = sum(levels_counts_dict.values())
        for specific_level, count in levels_counts_dict.items():
            years_broad_educations_to_specific_education_proportions[overall_level][specific_level] = count / total_count_of_level

    return years_broad_educations_to_specific_education_proportions


# Note: not deciding dropouts here, just moving graduates along
# Input: list of students
def graduate_students(students: [Individual], current_year: int):
    """
    Finds students who should be graduating and decides their destination (further education, working, unemployment,
    etc) based on the level of education they're graduating from

    :param students: A list of Individuals with an economic status of 'S'
    :param current_year: The current year of the simulation
    """

    to_graduate = list(filter(lambda student: (hasattr(student, 'graduation_date')) and (student.graduation_date == current_year), students))
    for grad in tqdm(to_graduate, desc="Graduates"):
        if grad.prospective_highest_level_of_education == "P":  # Primary School Kids continue
            grad.education = "P"
            grad.prospective_highest_level_of_education = "LS"
            grad.graduation_date = current_year + education_durations[2]
        elif grad.prospective_highest_level_of_education == "LS":  # Junior Cert Kids continue
            grad.education = "LS"
            grad.prospective_highest_level_of_education = "US"
            grad.graduation_date = current_year + education_durations[3]
        elif grad.prospective_highest_level_of_education in ["US", "PLC", "HC", "DGR", "PD", "D"]:
            remove_continue_education_and_normalise = False
            if hasattr(grad, 'education_to_be_achieved_in_lifetime'):
                if grad.education_to_be_achieved_in_lifetime <= education_to_number[
                        grad.prospective_highest_level_of_education]:  # Reached academic potential
                    remove_continue_education_and_normalise = True

            if grad.prospective_highest_level_of_education == "US":  # Leaving Cert kids decide
                # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
                progression_weights = [0.78, 0.16, 0.04, 0.01, 0.005, 0.005]
            elif grad.prospective_highest_level_of_education in ["PLC", "HC"]:  # Further Education people
                # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
                progression_weights = [0.4, 0.5, 0.07, 0.02, 0.005, 0.005]
            elif grad.prospective_highest_level_of_education == "DGR":  # Degree people
                # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
                progression_weights = [0.165, 0.765, 0.05, 0.01, 0.005, 0.005]
            elif grad.prospective_highest_level_of_education == "PD":  # Postgrad people
                # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
                progression_weights = [0.04, 0.82, 0.1, 0.025, 0.0075, 0.0075]
            # elif grad.prospective_highest_level_of_education == "D":  # PhD people
            else:  # PhD people
                # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
                progression_weights = [0.02, 0.9, 0.04, 0.025, 0.0075, 0.0075]

            if remove_continue_education_and_normalise:
                without_continue_education_sum = sum(p for p in progression_weights[1:])
                for idx, old_progression_weight in enumerate(progression_weights):
                    if idx == 0:
                        # Remove continue education as possibility
                        progression_weights[idx] = 0
                    else:
                        progression_weights[idx] = old_progression_weight / without_continue_education_sum

            finish_level_of_education_with_optional_continuance(grad, current_year, progression_weights)


# Progression proportions from: https://data.cso.ie/table/NPO03
def dropout_students(students: [Individual], current_year: int):
    """
    Removes a proportion of the student population from education (based on historical data)

    :param students: A list of Individuals with an economic status of 'S'
    :param current_year: The current year of the simulation
    :return: A list of students still in education
    """

    to_dropout = []

    for education_level_numeric, dropout_rate in education_dropout_rates.items():
        # Get numeric level of education
        if education_level_numeric in [2, 3]:
            # Equation from this table: https://data.cso.ie/table/EDQ07
            dropout_rate = (-0.5701*(current_year - 2004) + 14.176) / 100

            # 3 year long courses -> have to get the cube root of the completion rate
            dropout_rate = 1 - (1 - dropout_rate) ** (1. / 3)
            if dropout_rate < 0:
                dropout_rate = 0
        students_at_education_level = list(filter(
            lambda student: student.prospective_highest_level_of_education == number_to_education[education_level_numeric], students))
        num_students_at_education_level = len(students_at_education_level)

        num_students_at_education_level_to_dropout = round(num_students_at_education_level * dropout_rate)
        print(f"Education Level: {number_to_education[education_level_numeric]} | Dropout Rate: {dropout_rate}")

        if num_students_at_education_level_to_dropout > 0:
            not_at_potential_yet_or_no_defined_future_education = []
            above_potential = []
            for student in students_at_education_level:
                if hasattr(student, 'education_to_be_achieved_in_lifetime'):
                    if student.education_to_be_achieved_in_lifetime < education_level_numeric:
                        above_potential.append(student)
                    else:
                        not_at_potential_yet_or_no_defined_future_education.append(student)
                else:
                    not_at_potential_yet_or_no_defined_future_education.append(student)

            # Prioritise dropping out those who won't achieve this level
            num_students_who_wont_achieve_this_education_qualification = len(above_potential)

            if num_students_at_education_level_to_dropout > num_students_who_wont_achieve_this_education_qualification:
                to_dropout.extend(above_potential)

                to_dropout.extend(random.sample(not_at_potential_yet_or_no_defined_future_education,
                                                num_students_at_education_level_to_dropout -
                                                num_students_who_wont_achieve_this_education_qualification))
            else:
                to_dropout.extend(random.sample(above_potential,
                                                num_students_at_education_level_to_dropout))

    for dropout in tqdm(to_dropout, desc="Dropouts"):
        remove_continue_education_and_normalise = False
        if hasattr(dropout, 'education_to_be_achieved_in_lifetime'):
            if dropout.education_to_be_achieved_in_lifetime < education_to_number[
                    dropout.prospective_highest_level_of_education]:  # Reached academic potential
                remove_continue_education_and_normalise = True

        if dropout.prospective_highest_level_of_education in ["NF", "P", "LS"]:  # Junior Cert Kids dropout
            # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
            progression_weights = [0, 0.41, 0.5, 0.08, 0.01, 0.01]
        elif dropout.prospective_highest_level_of_education == "US":  # Leaving Cert kids dropout
            # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
            progression_weights = [0, 0.41, 0.5, 0.08, 0.01, 0.01]
        elif dropout.prospective_highest_level_of_education in ["PLC", "HC"]:  # Further Education people
            # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
            progression_weights = [0.31, 0.60, 0.08, 0.01, 0.005, 0.005]
        elif dropout.prospective_highest_level_of_education == "DGR":  # Degree people
            # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
            progression_weights = [0.4, 0.5, 0.07, 0.02, 0.005, 0.005]
        elif dropout.prospective_highest_level_of_education == "PD":  # Postgrad people
            # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
            progression_weights = [0.6, 0.2, 0.14, 0.04, 0.01, 0.01]
        else:  # PhD people
            # Order: [Continue education, W, UNE, UTWSD, LAHF, OTH]
            progression_weights = [0.6, 0.2, 0.14, 0.04, 0.01, 0.01]

        if remove_continue_education_and_normalise:
            without_continue_education_sum = sum(p for p in progression_weights[1:])
            for idx, old_progression_weight in enumerate(progression_weights):
                if idx == 0:
                    # Remove continue education as possibility
                    progression_weights[idx] = 0
                else:
                    progression_weights[idx] = old_progression_weight / without_continue_education_sum

        finish_level_of_education_with_optional_continuance(dropout, current_year, progression_weights, is_dropout=True)

    remaining_students = list(set(students) - set(to_dropout))
    return remaining_students


def add_children_to_school(total_population: [Individual], current_year: int):
    """
    Assigns children of the chosen school enrollment age an economic status of 'S' and allocates them to primary school

    :param total_population: The entire population of Ireland
    :param current_year: The current year of the simulation
    """

    to_enroll = list(filter(lambda person: person.age==school_enrollment_age, total_population))
    for enroller in tqdm(to_enroll, desc=f"Enrolling {school_enrollment_age} year olds in school"):
        enroller.economic_status = "S"
        enroller.graduation_date = current_year + education_durations[1]
        enroller.prospective_highest_level_of_education = "P"


def get_graduation_date_for_those_already_in_school(school_goers_of_relevant_age: [Individual], current_year):
    """
    Assigns a graduation data to children who do not have one based on their age

    :param school_goers_of_relevant_age: Students with an age <18
    :param current_year: The current year of the simulation
    """

    # for student in tqdm(school_goers_of_relevant_age, desc="School goers graduation date"):
    for student in school_goers_of_relevant_age:
        if not hasattr(student, 'graduation_date'):
            age = student.age
            primary_graduation_age = school_enrollment_age + education_durations[1]
            if school_enrollment_age <= age < primary_graduation_age:  # Primary
                student.graduation_date = current_year + (primary_graduation_age - age)
                student.prospective_highest_level_of_education = "P"
            elif primary_graduation_age <= age <= primary_graduation_age + education_durations[2]:
                student.education = "P"
                student.graduation_date = current_year + (primary_graduation_age + education_durations[2] - age)
                student.prospective_highest_level_of_education = "LS"
            else:
                student.education = "LS"
                student.graduation_date = current_year + (
                            primary_graduation_age + education_durations[2] + education_durations[3] - age)
                student.prospective_highest_level_of_education = "US"


def finish_level_of_education_with_optional_continuance(grad: Individual, current_year: int, progression_weights: list,
                                                        is_dropout=False):
    """
    This function assigns the future economic status, and cleans up other characteristics for an Individual who is
    leaving their current level of education

    :param grad: The Individual leaving their current level of education
    :param current_year: The current year of the simulation
    :param progression_weights: The Individual's probability of moving to each of the possible next steps
    :param is_dropout: A boolean which indicates whether the Individual is dropping out (or graduating)
    """

    next_steps = ["Continue Education", "W", "UNE", "UTWSD", "LAHF", "OTH"]

    # Award level of education if higher than current
    if (not is_dropout) and (education_to_number[grad.prospective_highest_level_of_education] > education_to_number[grad.education]):
        grad.education = grad.prospective_highest_level_of_education

    next_step = random.choices(next_steps, weights=progression_weights, k=1)[0]

    if next_step == "Continue Education":  # Continue Education
        grads_education_to_number = education_to_number[grad.education]

        grad.economic_status = "S"
        if hasattr(grad, 'education_to_be_achieved_in_lifetime'):
            grad.prospective_highest_level_of_education = decide_adults_course_to_undertake(grads_education_to_number,
                                        education_to_be_achieved_in_lifetime=grad.education_to_be_achieved_in_lifetime)
        else:
            grad.prospective_highest_level_of_education = decide_adults_course_to_undertake(grads_education_to_number)

        education_level_to_achieve = education_to_number[grad.prospective_highest_level_of_education]

        duration_of_said_education = education_durations[education_level_to_achieve]

        grad.graduation_date = current_year + duration_of_said_education
    else:  # Don't continue education
        del grad.prospective_highest_level_of_education
        del grad.graduation_date
        grad.economic_status = next_step


def assign_education_to_young_adults(young_adult_students: [Individual], year: int):
    """
    Estimates the level of education (NFQ levels 5-10) for young adult students

    :param young_adult_students: A list of students with ages >=18 and <25
    :param year: The current year of the simulation
    """

    total_proportion_of_students = plc_proportion + higher_cert_proportion + degree_proportion
    plc_proportion_of_students = plc_proportion / total_proportion_of_students
    hc_proportion_of_students = higher_cert_proportion / total_proportion_of_students
    # college_proportion_of_students = degree_proportion / total_proportion_of_students

    num_young_adult_students = len(young_adult_students)

    num_plc_students = round(plc_proportion_of_students * num_young_adult_students)
    num_hc_students = round(hc_proportion_of_students * num_young_adult_students)

    random.shuffle(young_adult_students)

    plc_students = [young_adult_students.pop() for _ in range(num_plc_students)]
    hc_students = [young_adult_students.pop() for _ in range(num_hc_students)]
    college_students = young_adult_students.copy()  # Remainder are college students

    for plc_student in plc_students:
        # Assume US education
        plc_student.education = "US"
        plc_student.graduation_date = random.choice(range(year, year+education_durations[4]+1))
        plc_student.prospective_highest_level_of_education = "PLC"

    for hc_student in hc_students:
        # Assume US education
        hc_student.education = "US"
        hc_student.graduation_date = random.choice(range(year, year+education_durations[5]+1))
        hc_student.prospective_highest_level_of_education = "HC"

    # Data from: https://data.cso.ie/table/HEO01
    for college_student in college_students:
        college_student.prospective_highest_level_of_education = random.choices(["DGR", "PD", "D"], [0.76, 0.22, 0.02], k=1)[0]
        if college_student.prospective_highest_level_of_education in ["PD", "D"]:
            # Assume previous level of education achieved
            previous_education_number = education_to_number[college_student.prospective_highest_level_of_education] - 1
            college_student.education = number_to_education[previous_education_number]
        else:
            # TODO: Get realistic previous educations for college students
            college_student.education = random.choices(["US", "PLC", "HC"], weights=[0.9, 0.05, 0.05], k=1)[0]

        # Randomly assign them some length along their college journey
        college_student.graduation_date = random.choice(range(year, year + education_durations[
            education_to_number[college_student.prospective_highest_level_of_education]] + 1))


# Input: list of students >=25
def assign_education_to_older_adults(older_adult_students: [Individual], year: int):
    """
    Estimates the prospective level of education (NFQ levels 5-10) for adult students over the age of 24 based on the
    rate of attainment of qulifications from the general adult population

    :param older_adult_students: A list of students with ages >=25
    :param year: The current year of the simulation
    """

    # Using educations of adults in age group
    for older in older_adult_students:
        older.education = random.choices(list(older_adult_educations_2022.keys()),
                                         weights=list(older_adult_educations_2022.values()), k=1)[0]

        to_take = decide_adults_course_to_undertake(education_to_number[older.education])
        older.prospective_highest_level_of_education = to_take

        # Randomly assign them some length along their education journey
        older.graduation_date = random.choice(range(year, year + education_durations[
            education_to_number[older.prospective_highest_level_of_education]] + 1))


# Adult data from: https://data.cso.ie/table/AES65
def decide_adults_course_to_undertake(current_level_of_education: int, education_to_be_achieved_in_lifetime=None):
    """
    Decides which level of education an adult learner will be enrolled into (based on their current level of education)

    :param current_level_of_education: The adults current level of education (as an integer)
    :param education_to_be_achieved_in_lifetime: The highest education level which the adult was previously predicted
        to attain
    :return: The level of education the adult will be assigned to study for
    """

    if current_level_of_education in [0, 1, 2]:  # NF, P, LS
        # Move to next level of education
        return list(education_to_number.keys())[list(education_to_number.values()).index(current_level_of_education + 1)]
    else:
        if current_level_of_education == 3:  # Has US
            possible_next_steps = ["PLC", "HC", "DGR"]
            possible_next_step_weights = [0.12, 0.03, 0.85]
        elif current_level_of_education == 4:  # Has PLC
            possible_next_steps = ["PLC", "HC", "DGR"]
            possible_next_step_weights = [0.41, 0.01, 0.58]
        elif current_level_of_education == 5:  # Has HC
            possible_next_steps = ["PLC", "HC", "DGR"]
            possible_next_step_weights = [0.1, 0.31, 0.58]
        elif current_level_of_education == 6:  # Has DGR
            #  (https://hea.ie/statistics/graduate-outcomes-data-and-reports/graduate-outcomes-all-years-2017-2024/)
            #  Further study - filter by award sought
            possible_next_steps = ["DGR", "PD", "D"]
            possible_next_step_weights = [0.12, 0.82, 0.06]
        elif current_level_of_education == 7:  # Has PD
            # Same source as above
            possible_next_steps = ["DGR", "PD", "D"]
            possible_next_step_weights = [0.15, 0.35, 0.5]
        elif current_level_of_education == 8:  # Has D
            # Same source as above
            possible_next_steps = ["DGR", "PD", "D"]
            possible_next_step_weights = [0.3, 0.2, 0.5]

        if education_to_be_achieved_in_lifetime:
            for i, next_step in enumerate(possible_next_steps):
                # Include all educations less than what this person is to achieve in their lifetime
                if education_to_number[next_step] > education_to_be_achieved_in_lifetime:
                    possible_next_steps = possible_next_steps[:i]
                    valid_next_step_weights = possible_next_step_weights[:i]
                    break
                elif i == len(possible_next_steps)-1:
                    # All next steps are valid, don't change possible_next_steps
                    valid_next_step_weights = possible_next_step_weights

            old_weights_sum = sum(p for p in valid_next_step_weights)
            possible_next_step_weights = [old_p/old_weights_sum for old_p in valid_next_step_weights]

        return random.choices(possible_next_steps, weights=possible_next_step_weights, k=1)[0]


def add_adult_back_to_education_system(person: Individual, year: int):
    """
    Assigns the extra education-based characteristics to an adult that is becoming a student

    :param person: The Individual who is becoming a student
    :param year: The current year of the simulation
    """

    persons_education_to_number = education_to_number[person.education]

    person.economic_status = "S"
    if hasattr(person, 'education_to_be_achieved_in_lifetime'):
        person.prospective_highest_level_of_education = decide_adults_course_to_undertake(persons_education_to_number,
                                                                                          person.education_to_be_achieved_in_lifetime)
    else:
        person.prospective_highest_level_of_education = decide_adults_course_to_undertake(persons_education_to_number)

    education_level_to_achieve = education_to_number[person.prospective_highest_level_of_education]

    duration_of_said_education = education_durations[education_level_to_achieve]

    person.graduation_date = year + duration_of_said_education


def educate_younger_adults_more_simply(younger_adults: [Individual], current_year: int):
    """
    Decides which young adults will be added back to formal education in the year, based on their current level of
    education and the education they have been predicted to attain in their lifetime

    :param younger_adults: The population aged between 18 and 24 (inclusive)
    :param current_year: The current year of the simulation
    """

    num_who_should_be_in_formal_education = round(proportion_of_younger_adults_that_should_be_students
                                                  * len(younger_adults))

    not_already_students = list(filter(lambda person: person.economic_status != "S",
                                       younger_adults))

    num_students_to_add = num_who_should_be_in_formal_education - \
                          (len(younger_adults) - len(not_already_students))

    not_at_potential_yet = []
    just_at_potential_or_no_defined_future_education = []
    for person in not_already_students:
        if not hasattr(person, 'education_to_be_achieved_in_lifetime'):
            just_at_potential_or_no_defined_future_education.append(person)
        else:
            if education_to_number[person.education] < person.education_to_be_achieved_in_lifetime:
                # Getting a higher qualification
                not_at_potential_yet.append(person)
            elif (education_to_number[person.education] == person.education_to_be_achieved_in_lifetime) and \
                    (person.education_to_be_achieved_in_lifetime > 3):
                # Going back for a qualification they already have
                # (not applicable for those who have mandatory increase of education - NF, P, LS, US)
                just_at_potential_or_no_defined_future_education.append(person)

    if num_students_to_add > 0:
        all_adult_learners_to_be_added_back = []
        # Add those not at their potential yet first
        if num_students_to_add > len(not_at_potential_yet):
            all_adult_learners_to_be_added_back.extend(not_at_potential_yet)

            # Then fill the rest out with those without defined future and those at potential already
            all_adult_learners_to_be_added_back.extend(
                random.sample(just_at_potential_or_no_defined_future_education,
                              num_students_to_add - len(not_at_potential_yet)))
        else:
            all_adult_learners_to_be_added_back = random.sample(not_at_potential_yet, num_students_to_add)

        for person in all_adult_learners_to_be_added_back:
            add_adult_back_to_education_system(person, year=current_year)


def educate_adults_more_simply(places: dict[str, Place], current_year: int):
    """
    Decides which adults will be returned to formal education based on their current education, predicted highest level
    of education to be achieved in their lifetime, and the regional adult student proportions

    :param places: A dictionary of EDs with ED_IDs being the keys, and their Place objects being the values
    :param current_year: The current year of the simulation
    """

    for region, constituent_counties in tqdm(regions_counties.items(), desc=f"Adult Education per region"):
        regions_whole_pop = []
        for county in constituent_counties:
            for ed_id in counties_ed_ids_stripped_no_repeats[county]:
                regions_whole_pop.extend(places[ed_id].population)

        region_age_eligible_population = list(filter(lambda person: 25 <= person.age <= 69, regions_whole_pop))
        for sex in ["M", "F"]:
            regions_sexes_population = list(filter(lambda person: person.sex == sex, region_age_eligible_population))

            for age_group, regions_proportion_of_people_in_sex_and_age_who_are_students in \
                    regional_adult_student_proportions_per_age_group_sexed[region][sex].items():

                split_age_range = age_group.split("_")
                lower_age_bound = int(split_age_range[0])
                upper_age_bound = int(split_age_range[1])

                regions_sexes_age_groups_population = [person for person in regions_sexes_population if
                                                       (lower_age_bound <= person.age <= upper_age_bound)]

                num_who_should_be_students = round(regions_proportion_of_people_in_sex_and_age_who_are_students
                                                              * len(regions_sexes_age_groups_population))

                not_already_students = list(filter(lambda person: person.economic_status != "S",
                                                   regions_sexes_age_groups_population))

                num_students_to_add = num_who_should_be_students - \
                                      (len(regions_sexes_age_groups_population) - len(not_already_students))

                not_at_potential_yet = []
                just_at_potential_or_no_defined_future_education = []

                for person in not_already_students:
                    if not hasattr(person, 'education_to_be_achieved_in_lifetime'):
                        just_at_potential_or_no_defined_future_education.append(person)
                    else:
                        if education_to_number[person.education] < person.education_to_be_achieved_in_lifetime:
                            # Getting a higher qualification
                            not_at_potential_yet.append(person)
                        elif (education_to_number[person.education] == person.education_to_be_achieved_in_lifetime) and \
                                (person.education_to_be_achieved_in_lifetime > 3):
                            # Going back for a qualification they already have
                            # (not applicable for those who have mandatory increase of education - NF, P, LS, US)
                            just_at_potential_or_no_defined_future_education.append(person)

                if num_students_to_add > 0:
                    all_adult_learners_to_be_added_back = []
                    # Add those not at their potential yet first
                    if num_students_to_add > len(not_at_potential_yet):
                        all_adult_learners_to_be_added_back.extend(not_at_potential_yet)

                        # Then fill the rest out with those without defined future and those at potential already
                        if num_students_to_add - len(not_at_potential_yet) < len(just_at_potential_or_no_defined_future_education):

                            all_adult_learners_to_be_added_back.extend(
                                random.sample(just_at_potential_or_no_defined_future_education,
                                              num_students_to_add - len(not_at_potential_yet)))
                        else:  # More people to be added than there are in age group
                            all_adult_learners_to_be_added_back.extend(just_at_potential_or_no_defined_future_education)
                    else:
                        all_adult_learners_to_be_added_back = random.sample(not_at_potential_yet,
                                                                            num_students_to_add)

                    for person in all_adult_learners_to_be_added_back:
                        add_adult_back_to_education_system(person, year=current_year)


# Input: Everyone except students and children
def sort_out_ns_education(non_student_adults: [Individual]):
    """
    This is a helper function to assign valid educations to Individuals who were assigned a value of 'Not Stated' or
    'Not Applicable'

    :param non_student_adults: Adult Individuals who do not have an economic status of 'S' (student)
    """

    print("- Sorting out people with NS or NA (and not students) education\n")
    people_with_invalid_education = [person for person in non_student_adults if (person.education == "NS")
                                     or ((person.education == "NA")
                                         and (person.economic_status != "S")
                                         and (person.age >= 15))]

    people_with_valid_education = [person for person in non_student_adults if person.education not in ["NS", "NA"]]

    age_groups = [(f"{i}_{i+4}") for i in range(0, 81, 5)]
    age_groups.append("GE_85")
    age_sex_education_counts = {}
    for person in people_with_valid_education:
        for age_group in age_groups:
            if age_group != "GE_85":
                age_group_lower_bound = int(age_group.split("_")[0])
                age_group_upper_bound = int(age_group.split("_")[1])
                if (person.age < age_group_lower_bound) or (person.age > age_group_upper_bound): # Incorrect age group
                    continue

            key = (age_group, person.sex)
            if key not in age_sex_education_counts:
                age_sex_education_counts[key] = {}

            if person.education not in age_sex_education_counts[key]:
                age_sex_education_counts[key][person.education] = 1
            else:
                age_sex_education_counts[key][person.education] += 1

    age_sex_education_proportions = {}
    for key, education_counts in age_sex_education_counts.items():
        people_in_age_and_sex = sum(list(education_counts.values()))

        age_sex_education_proportions[key] = {}
        for education, count in education_counts.items():
            age_sex_education_proportions[key][education] = count / people_in_age_and_sex

    for (age_group, sex), education_proportions in age_sex_education_proportions.items():
        if age_group != "GE_85":
            age_group_lower_bound = int(age_group.split("_")[0])
            age_group_upper_bound = int(age_group.split("_")[1])
            invalid_people_in_category = [person for person in people_with_invalid_education if
                                     (age_group_lower_bound <= person.age <= age_group_upper_bound)
                                     and (person.sex == sex)]
        else:
            invalid_people_in_category = [person for person in people_with_invalid_education if
                                     (person.age >= 85)
                                     and (person.sex == sex)]

        educations = random.choices(list(education_proportions.keys()),
                                    weights=list(education_proportions.values()), k=len(invalid_people_in_category))
        for idx, ns_person in enumerate(invalid_people_in_category):
            ns_person.education = educations[idx]


if __name__ == '__main__':
    # Graduation testing
    this_year = 2023
    should_graduate = []
    for _ in range(100):
        person_to_add = Individual(age=18, sex=random.choice(["M", "F"]), marital_status="SGL", education="LS", economic_status="S", ed="68013",
                                   current_year=this_year)
        person_to_add.graduation_date = 2023
        person_to_add.prospective_highest_level_of_education = "US"
        person_to_add.education_to_be_achieved_in_lifetime = random.choice([3,4,5,6,7,8])
        should_graduate.append(person_to_add)

    graduate_students(should_graduate, this_year)

    does_continue_count = 0
    does_not_continue_count = 0
    for shouldve_grad in should_graduate:
        if shouldve_grad.economic_status == "S":
            does_continue_count += 1
            print("Goes on to further education!")
            print(f"Prospective: {shouldve_grad.prospective_highest_level_of_education}")
            print(f"To be achieved: {shouldve_grad.education_to_be_achieved_in_lifetime}")
            print(f"Graduation Date: {shouldve_grad.graduation_date}\n")
        else:
            does_not_continue_count += 1
            print("Does not go on to further education!")
            print(f"Economic Status: {shouldve_grad.economic_status}")
            print(f"To be achieved: {shouldve_grad.education_to_be_achieved_in_lifetime}\n")

    print(f"Continuers: {does_continue_count}")
    print(f"Non-continuers: {does_not_continue_count}")