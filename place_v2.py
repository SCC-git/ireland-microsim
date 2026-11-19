from individual import Individual
import utils


class Place:
    def __init__(self,
                 ed_id: str,
                 county:str=None,
                 region:str=None,
                 static_generation_approach:str="ipf"):
        """
        Creates an ED object and assigns it a population of Individual objects

        :param ed_id: The ED's ED_ID
        :param county: The county in which the ED is situated
        :param region: The NUTS3 region in which the ED is situated
        :param static_generation_approach: The static generation approach folder to look for a population for the ED in
        """

        self.ed_id = ed_id

        if county:
            self.county = county
        if region:
            self.region = region

        population_folder = f"./populations/{static_generation_approach}/"
        self.population = utils.create_eds_individuals_from_population(population_folder, ed_id)

    def add_people_to_places_population(self, people_to_add: [Individual], from_abroad=False):
        """
        Adds Individuals to the ED's population and makes their ED characteristic this ED
        :param people_to_add: The list of Individuals to add
        :param from_abroad: A boolean which denotes whether the person is an international or internal immigrant
        """

        for person_to_add in people_to_add:
            person_to_add.ed = self.ed_id
            person_to_add.came_from_abroad = from_abroad

            self.population.append(person_to_add)

    def update_with_deaths(self, year, years_mortality_rates):
        """
        Updates the ED's population once all of the deaths for the year have been calculated and ages all survivors
        :param year: The current year of the simulation
        :param years_mortality_rates: The mortality rates for the year
        :return: The net population change due to mortality in the ED
        """
        initial_population = len(self.population)

        surviving_population = [person for person in self.population if person.should_survive(year, years_mortality_rates)]

        self.population = surviving_population
        for person in self.population:
            # Age surviving population one year
            person.age += 1

        surviving_population = len(self.population)

        return initial_population - surviving_population


if __name__ == '__main__':
    # Test
    test_ed_id = "068013"  # Newcastle
    test_county = "Galway"
    test_region = "West"
    test_static_generation_approach = "ipf"
    test_place = Place(ed_id=test_ed_id, county=test_county, region=test_region,
                       static_generation_approach=test_static_generation_approach)
    print(f"Newcastle Population: {len(test_place.population)}")
