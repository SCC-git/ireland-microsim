import copy
import os.path
import fertility
from place_v2 import Place
import pandas as pd
from constants import regions_counties, \
    counties_ed_ids_stripped_no_repeats, \
    regional_age_specific_fertility_rates_2022, mortality_by_age_2016
from individual import Individual
from tqdm import tqdm
import pickle as pkl
from datetime import datetime
import sys
import argparse
import education
import migration
import employment
import relationships
import citizenship


def setup(initial_population: [Individual], start_year: int, places: dict[str, Place]):
    """
    A helper function which calls a number of other functions to fix invalid characteristic values that may have been
    assigned from the population loading process. Citizenship, education and marital statuses are handled.

    :param initial_population: The population before the simulation begins
    :param start_year: The simulation start year
    :param places: A dictionary of EDs with ED_IDs being the keys, and their Place objects being the values
    """
    print("-"*50)
    print("SETUP")

    # Sort out NS citizenship
    citizenship.sort_out_ns_citizenship(initial_population)

    # Sort out NS education
    non_student_adults = [person for person in initial_population
                          if (person.age >= 15) and (person.economic_status != "S")]
    education.sort_out_ns_education(non_student_adults)

    # Set up education
    students = [person for person in initial_population if (person.economic_status=="S")]
    education.estimate_level_of_education_for_students(students, start_year)

    # Set up marital statuses
    for region, constituent_counties in regions_counties.items():
        regions_population = []
        for county in constituent_counties:
            for ed_id in counties_ed_ids_stripped_no_repeats[county]:
                if ed_id in places:  # TODO: Remove this for full simulations
                    regions_population.extend(places[ed_id].population)

        print(f"- Doing the marriages for: {region}")

        # Initially, join people who were married at the start of the simulation
        print("- Marrying those who are already married but do not have a spouse")
        married_pop_in_region = list(filter(lambda person: (person.marital_status == "MAR")
                                                           and (not hasattr(person, "spouse")),
                                            regions_population))

        relationships.match_couples_to_be_married_in_region_no_specified_sexualities(married_pop_in_region)
        print(f"- Marriages completed in {region}\n")

    print("SETUP COMPLETE")
    print("-"*50)


def main(raw_args=None):
    """
    The main simulation controller. Figures out the simulation scenarios, loads the initial population and calls each
    module in the desired order. Saves the population and prints statistics at the conclusion of the simulation

    :param raw_args: The command line inputs which decide on the simulation scenario
    """

    output_to_file = False
    if output_to_file:
        orig_stdout = sys.stdout
        f = open(f"./output_txt_files/test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w")
        sys.stdout = f

    parser = argparse.ArgumentParser()
    parser.add_argument("-im", "--international",
                        choices=["M1", "M2", "M3", "custom", "actual", "new_M1", "new_M2", "new_M3"],
                        nargs="?", const="M1", type=str)
    parser.add_argument("-f", "--fertility", choices=["F1", "F2", "actual", "new"], nargs="?", const="F2", type=str)
    parser.add_argument("-dub_outflow", action="store_true")
    parser.add_argument("-dub_inflow", dest="dub_outflow", action="store_false")  # This is the best way to do booleans
    parser.add_argument("-t", "--timestamp", nargs="?", const=datetime.now().strftime("%Y%m%d_%H%M%S"), type=str)

    args = parser.parse_args(raw_args)

    # CSO Assumptions
    international_migration_scenario = args.international
    fertility_scenario = args.fertility
    dublin_outflow = args.dub_outflow
    if args.timestamp:
        timestamp = args.timestamp
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Running main with "
          f"{international_migration_scenario} international migration, "
          f"{fertility_scenario} fertility, and "
          f"Dublin {'outflow' if dublin_outflow else 'inflow'}"
          f" at {timestamp}")

    start_year = 2022
    end_year = 2058
    static_generation_approach = "ipf_rescaled_pop"
    save_population = False
    save_initial_population = False  # This terminates the program when the initial population is saved
    save_at_checkpoints = False
    checkpoints = [2027, 2032, 2037, 2042, 2047, 2052]
    save_every_year = False

    results_folder = "./results/post_viva/" + timestamp + f"_{start_year}_{end_year}_{fertility_scenario}_dublin_{'outflow' if dublin_outflow else 'inflow'}_" \
                                                                      f"{international_migration_scenario}_international_migration_{static_generation_approach}/"

    if not os.path.exists(results_folder):
        os.makedirs(results_folder)
        os.makedirs(results_folder + "populations/")
    print(results_folder)

    # Going to add data in the order:
    # {Year: [starting_population, deaths, net internal migration, net international migration, births, TFR, ending_population]}
    annual_places_population_dfs = {}

    population_folder = f"./populations/{static_generation_approach}/"

    # Get ED IDs
    areas_of_interest = [f.split(".")[0] for f in os.listdir(population_folder) if f[-4:]==".pkl"]

    places = {}
    f2_fertility_rates = copy.deepcopy(regional_age_specific_fertility_rates_2022)

    pops = []
    for area in tqdm(areas_of_interest, desc="Population Initialisation"):
        found_areas_region = False
        for county, constituent_eds_ids in counties_ed_ids_stripped_no_repeats.items():
            if area in constituent_eds_ids:
                areas_county = county
                break

        for higher_region, constituent_counties in regions_counties.items():
            if areas_county in constituent_counties:
                areas_region = higher_region
                found_areas_region = True
                break

        if not found_areas_region:
            raise ValueError(f"No region found for {area}")

        places[area] = Place(ed_id=area, county=areas_county, region=areas_region, static_generation_approach=static_generation_approach)
        pops.append(len(places[area].population))
        annual_places_population_dfs[area] = {"Year": [], "Starting Population": [], "Deaths": [],
                                              "Net Internal Migration": [],
                                              "Net International Migration": [], "Births": [],
                                              "Ending Population": [], "TFR": []}

    # Transform to 2022 values
    years_mortality_rates = copy.deepcopy(mortality_by_age_2016)

    for sex, age_specific_mortality_rates in years_mortality_rates.items():
        for age, original_mortality_rate in age_specific_mortality_rates.items():
            # years_mortality_rates[sex][age] = original_mortality_rate * 0.975
            # years_mortality_rates[sex][age] = original_mortality_rate * 1.01
            # years_mortality_rates[sex][age] = original_mortality_rate * 1.03
            years_mortality_rates[sex][age] = original_mortality_rate * 1

    print(f"Total population: {sum(pops)}\n")

    ireland_initial_population = []
    for _, place in places.items():
        ireland_initial_population.extend(place.population)

    setup(ireland_initial_population, start_year, places)

    if save_initial_population:
        properly_set_up_ireland_initial_population = []
        for _, place in places.items():
            properly_set_up_ireland_initial_population.extend(place.population)

        with open("ireland_population_2022.pkl", "wb") as f:
            pkl.dump(properly_set_up_ireland_initial_population, f)
        return

    for year in range(start_year+1, end_year):
        print(f"BEGINNING {year} at {datetime.now()}")

        if year != start_year:
            for region in regions_counties.keys():
                # F2 Fertility
                if fertility_scenario == "F2":
                    # Decrease fertility rates from 1.8 to 1.6 over 15 years
                    # 15th root of 1.6/1.8 is 0.992178545
                    # CHANGING THIS TO 0.991593358
                    # This is because the actual initial TFR is 1.816
                    if 2016 < year <= 2031:
                        for age_group, original_value in f2_fertility_rates[region].items():
                            f2_fertility_rates[region][age_group] = 0.991593358 * original_value

                elif fertility_scenario == "new":
                    # Decrease fertility rates from 1.55 to 1.3 over 15 years
                    # 15th root of 1.3/1.55 is 0.988342437
                    if 2023 <= year <= 2038:
                        for age_group, original_value in f2_fertility_rates[region].items():
                            f2_fertility_rates[region][age_group] = 0.988342437 * original_value

            for ed_id, ed_place in places.items():
                annual_places_population_dfs[ed_id]["Year"].append(year)
                annual_places_population_dfs[ed_id]["Starting Population"].append(len(ed_place.population))

                places_tfr = sum(f2_fertility_rates[ed_place.region].values()) * 5 / 1000
                annual_places_population_dfs[ed_id]["TFR"].append(places_tfr)

        print(f" - Calculating deaths in {year}")
        state_deaths = 0

        for sex, age_specific_mortality_rates in years_mortality_rates.items():
            for age, original_mortality_rate in age_specific_mortality_rates.items():
                if year < 2047:
                    improvement_amount_this_year = (0.975 + ((0.985 - 0.975) / (2047 - 2022)) * (year - 2022))
                else:
                    improvement_amount_this_year = 0.985

                if age <= 90:
                    years_mortality_rates[sex][age] = original_mortality_rate * improvement_amount_this_year
                else:
                    ninety_year_olds_improved_mortality_percentage = improvement_amount_this_year
                    adjusted_improvement = ninety_year_olds_improved_mortality_percentage + \
                                                              ((age - 90) / (100 - 90)) * \
                                                              (1 - ninety_year_olds_improved_mortality_percentage)
                    years_mortality_rates[sex][age] = original_mortality_rate * adjusted_improvement

        for name, place in tqdm(places.items(), desc="Places with deaths completed"):
            deaths = place.update_with_deaths(year, years_mortality_rates)

            state_deaths += deaths

            annual_places_population_dfs[name]["Deaths"].append(deaths)

        print(f" - # Deaths in {year}: {state_deaths}")

        print(f" - Calculating internal migration in {year}")
        regional_net_internal_migration = migration.\
            internal_migrants_ed_with_realistic_destination_proportions_and_migrants(dublin_outflow, places)

        print(f" - Calculating international migration in {year}")
        regional_net_international_migration = migration. \
            international_migration_eds_with_csos_average_realistic_proportions_with_citizenship_correct_net_migrations(
            international_migration_scenario, places, year)

        print(f" - Calculating births in {year}")
        births_per_ed = fertility.regional_births(places, year, f2_fertility_rates)
        print(f" - # Births in {year}: {sum(births_per_ed.values())}")

        # All steps that affect population size complete for the year

        print(f" - Calculating divorces, separations and marriages in {year}")
        # Break up existing marriages and create new marriages
        relationships.annual_relationship_loop(places)

        print(f" - Calculating education changes in {year}")
        # Education
        education.education_loop(places, current_year=year)

        print(f" - Calculating economic status changes in {year}")
        # Employment
        employment.change_peoples_economic_statuses_v3(places)

        for place_id, place in places.items():
            # Log internal migration, international migration, births, ending population
            annual_places_population_dfs[place_id]["Net Internal Migration"].append(
                regional_net_internal_migration[place_id])
            annual_places_population_dfs[place_id]["Net International Migration"].append(
                regional_net_international_migration[place_id])
            if place_id in births_per_ed:
                annual_places_population_dfs[place_id]["Births"].append(births_per_ed[place_id])
            else:
                annual_places_population_dfs[place_id]["Births"].append(0)
            annual_places_population_dfs[place_id]["Ending Population"].append(len(places[place_id].population))
        print("-"*50)

        if save_every_year:
            years_population = []
            for _, place in places.items():
                years_population.extend(place.population)

            with open(f"{results_folder}populations/{year}_population.pkl", "wb") as f:
                pkl.dump(years_population, f)

        if save_at_checkpoints:
            if year in checkpoints:
                checkpoint_population = []
                for _, place in places.items():
                    checkpoint_population.extend(place.population)

                with open(f"{results_folder}populations/checkpoint_population_{year}.pkl", "wb") as f:
                    pkl.dump(checkpoint_population, f)

    population_for_saving = []
    for area_id, annual_stats_dict in annual_places_population_dfs.items():
        areas_df = pd.DataFrame.from_dict(annual_stats_dict)
        areas_df = areas_df.set_index("Year")
        areas_df.to_csv(f"{results_folder}" + f"{area_id}.csv")

        if save_population:
            population_for_saving.extend(places[area_id].population)

    if save_population:
        with open(f"{results_folder}populations/population.pkl", "wb") as f:
            pkl.dump(population_for_saving, f)

    print(f"\nSimulation Complete")
    for area in areas_of_interest:
        print(f"\t{area} population: {len(places[area].population)}")

    if output_to_file:
        sys.stdout = orig_stdout
        f.close()


if __name__ == '__main__':
    # Test
    main(["-im", "new_M1", "-f", "new", "-dub_outflow"])
