import random
from individual import Individual


def sort_out_ns_citizenship(people: [Individual]):
    """
    This is a helper function to assign valid citizenships to Individuals who were assigned a value of 'Not Stated'

    :param people: A list of individuals, some of whom may have a citizenship of 'NS'
    """

    print("- Sorting out people with NS citizenship\n")
    # Sort out people with "NS" as citizenship
    people_with_invalid_citizenship = [person for person in people if (person.citizenship == "NS")]

    people_with_valid_citizenship = [person for person in people if person.citizenship != "NS"]

    age_groups = [(f"{i}_{i+4}") for i in range(0, 81, 5)]
    age_groups.append("GE_85")
    age_sex_citizenship_counts = {}
    for person in people_with_valid_citizenship:
        for age_group in age_groups:
            if age_group != "GE_85":
                age_group_lower_bound = int(age_group.split("_")[0])
                age_group_upper_bound = int(age_group.split("_")[1])
                if (person.age < age_group_lower_bound) or (person.age > age_group_upper_bound): # Incorrect age group
                    continue

            key = (age_group, person.sex)
            if key not in age_sex_citizenship_counts:
                age_sex_citizenship_counts[key] = {}

            if person.citizenship not in age_sex_citizenship_counts[key]:
                age_sex_citizenship_counts[key][person.citizenship] = 1
            else:
                age_sex_citizenship_counts[key][person.citizenship] += 1

    age_sex_citizenship_proportions = {}
    for key, citizenship_counts in age_sex_citizenship_counts.items():
        people_in_age_and_sex = sum(list(citizenship_counts.values()))

        age_sex_citizenship_proportions[key] = {}
        for citizenship, count in citizenship_counts.items():
            age_sex_citizenship_proportions[key][citizenship] = count / people_in_age_and_sex

    for (age_group, sex), citizenship_proportions in age_sex_citizenship_proportions.items():
        if age_group != "GE_85":
            age_group_lower_bound = int(age_group.split("_")[0])
            age_group_upper_bound = int(age_group.split("_")[1])
            invalid_people_in_category = [person for person in people_with_invalid_citizenship if
                                          (age_group_lower_bound <= person.age <= age_group_upper_bound)
                                          and (person.sex == sex)]
        else:
            invalid_people_in_category = [person for person in people_with_invalid_citizenship if
                                          (person.age >= 85)
                                          and (person.sex == sex)]

        citizenships = random.choices(list(citizenship_proportions.keys()),
                                      weights=list(citizenship_proportions.values()), k=len(invalid_people_in_category))
        for idx, ns_person in enumerate(invalid_people_in_category):
            ns_person.citizenship = citizenships[idx]