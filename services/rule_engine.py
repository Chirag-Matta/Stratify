# services/rule_engine.py

def evaluate(rules: dict, user_stats: dict) -> bool:
    if "operator" in rules:
        op = rules["operator"]
        results = [evaluate(cond, user_stats) for cond in rules["conditions"]]

        if op == "AND":
            return all(results)
        elif op == "OR":
            return any(results)
        else:
            raise ValueError(f"Unsupported operator {op}")

    # Leaf condition
    field = rules["field"]
    operator = rules["op"]
    value = rules["value"]

    user_value = user_stats.get(field)
    if user_value is None:
        return False

    if operator == "gt":
        return user_value > value
    if operator == "gte":
        return user_value >= value
    if operator == "lt":
        return user_value < value
    if operator == "lte":
        return user_value <= value
    if operator == "eq":
        return user_value == value
    if operator == "neq":
        return user_value != value
    if operator == "in":
        return user_value in value
    if operator == "not_in":
        return user_value not in value

    raise ValueError(f"Unsupported operator {operator}")