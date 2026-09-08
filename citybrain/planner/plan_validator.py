class PlanValidator:

    def validate(self, plan, state):

        # Check whether the plan exists
        if plan is None:
            return False

        # Check every road in the planned route
        for edge in plan.route:

            road = state.get("roads", {}).get(edge, {})

            # If road is blocked, plan is invalid
            if road.get("blocked", False):
                return False

        return True