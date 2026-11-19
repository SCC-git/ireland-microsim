from __future__ import annotations
from numpy import random


class Individual:

    # def __init__(self, age: int = random.randint(0, 100), sex=random.choice(["Female", "Male"])):
    # Had the above approach previously but it didn't work
    # Because python evaluates default argument expression when you create the function/class
    # Not when you call the function/class

    def __init__(self,
                 age: int,
                 sex: str,
                 marital_status: str=None,
                 # house_size: str=None,
                 citizenship: str=None,
                 moved_to_ireland_in_last_year: bool=False,
                 economic_status: str=None,
                 education: str=None,
                 parents: [Individual] = None,  # Can be just mother or both
                 ed: str = None,
                 born_in_simulation: bool = False,
                 current_year: int = None):
        """
        Creates an Individual object with the assigned characteristics

        :param age: An integer
        :param sex: 'M' or 'F'
        :param marital_status: "SGL", "MAR", "WID", or "SEP"
        :param citizenship: "IE", "UK", "EU", or "RW"
        :param moved_to_ireland_in_last_year: Boolean
        :param economic_status: W", "UNE", "R", "UTWSD", "S", "LAHF", "OTH", or "NA"
        :param education: "NF", "P", "LS", "US", "PLC", "HC", "DGR", "PD", "D", or "NA"
        :param parents: The person's parent(s) (Individual objects)
        :param ed: Their home ED (the ED_ID)
        :param born_in_simulation: Boolean
        :param current_year: The current year of the simulation
        """

        self.age = age

        self.sex = sex

        if not marital_status:
            self.marital_status = random.choice(["SGL", "MAR", "WID", "SEP"])
        else:
            self.marital_status = marital_status

        if not citizenship:
            self.citizenship = random.choice(["IE", "UK", "EU", "RW"])
        else:
            self.citizenship = citizenship

        self.moved_to_ireland_in_last_year = moved_to_ireland_in_last_year

        if not economic_status:
            self.economic_status = random.choice(["W", "UNE", "R", "UTWSD", "S", "LAHF", "OTH", "NA"])
        else:
            self.economic_status = economic_status

        if not education:
            self.education = random.choice(["NF", "P", "LS", "US", "PLC", "HC", "DGR", "PD", "D", "NA"])
        else:
            self.education = education

        # This is a cool feature if you have lots of memory available
        # self.history = {self.age: [f"Spawned with Age: {self.age} "
        #                             f"| Sex: {self.sex}"
        #                             f"| Marital Status: {self.marital_status}"
        #                             f"| Economic Status: {self.economic_status}"
        #                             f"| Education: {self.education} "]}

        if ed:
            self.ed = ed

        if parents:
            self.parents = parents

        if born_in_simulation:
            self.birth_year = current_year
        else:
            self.birth_year = current_year - age

    # A neat feature which tracks all if the changes to a person's attributes (memory-intensive)
    # def __setattr__(self, key, value):
    #     if key != "history":
    #         if not hasattr(self, 'age'):
    #             age_key = value
    #         else:
    #             age_key = self.age
    #
    #         if age_key not in self.history:
    #             self.history[age_key] = []
    #
    #         if hasattr(self, key):
    #             current_attribute_value = getattr(self, key)
    #             if current_attribute_value != value:
    #                 self.history[age_key].append(f"{key}: {current_attribute_value} > {value}")
    #         else:
    #             self.history[age_key].append(f"{key} created with value: {value}")
    #
    #     super().__setattr__(key, value)
    #
    # def __delattr__(self, item):
    #     if self.age not in self.history:
    #         self.history[self.age] = []
    #
    #     self.history[self.age].append(f"{item} deleted")
    #
    #     super().__delattr__(item)

    def __str__(self):
        """
        Returns a string representation of the individual's important characteristics

        :return: the string
        """
        string_rep = f"Sex: {self.sex} | Age: {self.age} | Marital Status: {self.marital_status} | " \
                     f"Citizenship: {self.citizenship} | " \
                     f"Moved to Ireland in last year: {self.moved_to_ireland_in_last_year} | " \
                     f"Economic Status: {self.economic_status} | Education: {self.education} | ED: {self.ed}"
        return string_rep

    def should_survive(self, year, years_mortality_rates: dict):
        """
        Decides whether the Individual should survive the year based on their age, sex and the year's mortality rates.
        References to and from Individuals who do not survive are removed

        :param year: The current year of the simulation
        :param years_mortality_rates: A dictionary representing the per-sex, per-age mortality rates for the year
        :return: a boolean indicating whether the person survived or not
        """

        if self.age >= 105:  # Beyond the valid age for our simulation, kill
            self.remove_references_to_and_from_person()
            # if self.age not in self.history:
            #     self.history[self.age] = []
            # self.history[self.age].append(f"Died in {year}")
            return False
        else:
            chance_of_dying_in_last_year = years_mortality_rates[self.sex][self.age]

            chance_of_dying_in_last_year = float(chance_of_dying_in_last_year)
            if chance_of_dying_in_last_year > random.uniform(0, 1):
                # Kill - Remove references to person that could exist elsewhere
                self.remove_references_to_and_from_person()
                # if self.age not in self.history:
                #     self.history[self.age] = []
                # self.history[self.age].append(f"Died in {year}")
                return False

        return True

    def remove_references_to_and_from_person(self, emigrate=False):
        """
        Removes inter-Individual references from an Individual that is being removed from the population (whether
        through death or emigration)

        :param emigrate: a Boolean indicating whether the person is emigrating (or dying)
        """
        if hasattr(self, 'spouse') and self.spouse != "Outsider":
            if emigrate:
                self.spouse.spouse = "Outsider"
            else:
                try:
                    del self.spouse.spouse
                except AttributeError:
                    print("Spouse doesn't exist", self.spouse)
                self.spouse.marital_status = "WID"

        if hasattr(self, 'children'):
            for child in self.children:
                child.parents.remove(self)

        if hasattr(self, 'parents'):
            for parent in self.parents:
                parent.children.remove(self)
