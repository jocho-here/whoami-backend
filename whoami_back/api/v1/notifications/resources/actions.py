from sqlalchemy import text

from whoami_back.utils.db import to_csv, to_ref_csv

actions_data = [
    {
        "id_0": "ba9aba94-b7be-42db-bd73-6fd84153f3c2",
        "message_0": "started following you",
    },
    {
        "id_1": "00a4356a-46ba-427f-b858-670cb76f0a42",
        "message_1": "requested to follow you",
    },
    {
        "id_2": "1c2b36d2-a05a-454a-a016-75183f023829",
        "message_2": "accepted your follow request",
    },
    {
        "id_3": "210da5f9-2a65-447e-b860-3ea8becac628",
        "message_3": "shared a new post",
    },
]


def get_insert_actions_query_text():
    values = []
    flattened_params = {}

    for i, action_data in enumerate(actions_data):
        values.append(f"({to_ref_csv(action_data.keys())})")

        for key in action_data:
            flattened_params[key] = action_data[key]

    insert_query = f"""
INSERT INTO notification_action (id, message)
VALUES {to_csv(values)}
    """

    return text(insert_query).bindparams(**flattened_params)
