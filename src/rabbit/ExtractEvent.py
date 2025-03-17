# no imports required


def unpackJson(json_response):
    """
    args:
        json_response (json): The json response (max 100) obtained by querying the data using GitHub REST API for an user account

    returns:
        events (list): List of dictionaries, where each dictionary contains the details corresponding to each event done
                       by an account and present in the json response

    method:
        Unpacks the json response (queried data using GitHub REST API for an user account) into a dictionary with the
        mandatory fields event_id, event_type, login, repository, created_at and unique identifiers for the events such
        as issue_node_id, push_id and so on.
    """

    events = []
    for jr in range(len(json_response)):
        info_dict = {}
        event_type = json_response[jr].get("type")
        info_dict["event_id"] = json_response[jr].get("id")
        info_dict["event_type"] = json_response[jr].get("type")
        info_dict["login"] = json_response[jr].get("actor", {}).get("login")
        info_dict["repository"] = json_response[jr].get("repo", {}).get("name")
        info_dict["created_at"] = json_response[jr].get("created_at")
        if event_type == "PushEvent":
            info_dict["push_id"] = json_response[jr].get("payload", {}).get("push_id")

        if (
            event_type == "PullRequestReviewEvent"
            or event_type == "PullRequestEvent"
            or event_type == "PullRequestReviewCommentEvent"
        ):
            info_dict["action"] = json_response[jr].get("payload", {}).get("action")
            info_dict["PR_number"] = (
                json_response[jr]
                .get("payload", {})
                .get("pull_request", {})
                .get("number")
            )
            info_dict["state"] = (
                json_response[jr]
                .get("payload", {})
                .get("pull_request", {})
                .get("state")
            )
            info_dict["PR_node_id"] = (
                json_response[jr]
                .get("payload", {})
                .get("pull_request", {})
                .get("node_id")
            )

            if event_type == "PullRequestEvent":
                info_dict["merged"] = (
                    json_response[jr]
                    .get("payload", {})
                    .get("pull_request", {})
                    .get("merged")
                )

            elif event_type == "PullRequestReviewCommentEvent":
                info_dict["comment_node_id"] = (
                    json_response[jr]
                    .get("payload", {})
                    .get("comment", {})
                    .get("node_id")
                )

            elif event_type == "PullRequestReviewEvent":
                info_dict["review_state"] = (
                    json_response[jr].get("payload", {}).get("review", {}).get("state")
                )
                info_dict["review_node_id"] = (
                    json_response[jr]
                    .get("payload", {})
                    .get("review", {})
                    .get("node_id")
                )

        elif event_type == "IssueCommentEvent" or event_type == "IssuesEvent":
            if "/pull/" in json_response[jr].get("payload").get("issue", {}).get(
                "html_url"
            ):
                info_dict["PR_number"] = (
                    json_response[jr].get("payload", {}).get("issue", {}).get("number")
                )
                info_dict["PR_node_id"] = (
                    json_response[jr].get("payload", {}).get("issue", {}).get("node_id")
                )
                info_dict["PR_closed_at"] = (
                    json_response[jr]
                    .get("payload", {})
                    .get("issue", {})
                    .get("closed_at")
                )
            else:
                info_dict["issue_number"] = (
                    json_response[jr].get("payload", {}).get("issue", {}).get("number")
                )
                info_dict["issue_node_id"] = (
                    json_response[jr].get("payload", {}).get("issue", {}).get("node_id")
                )
                info_dict["issue_closed_at"] = (
                    json_response[jr]
                    .get("payload", {})
                    .get("issue", {})
                    .get("closed_at")
                )
            info_dict["action"] = json_response[jr].get("payload", {}).get("action")
            info_dict["state"] = (
                json_response[jr].get("payload", {}).get("issue", {}).get("state")
            )
            info_dict["num_comments"] = (
                json_response[jr].get("payload", {}).get("issue", {}).get("comments")
            )

            if event_type == "IssueCommentEvent":
                info_dict["comment_node_id"] = (
                    json_response[jr]
                    .get("payload", {})
                    .get("comment", {})
                    .get("node_id")
                )

        elif event_type == "DeleteEvent" or event_type == "CreateEvent":
            info_dict["ref"] = json_response[jr].get("payload", {}).get("ref")
            info_dict["ref_type"] = json_response[jr].get("payload", {}).get("ref_type")

        elif event_type == "CommitCommentEvent":
            info_dict["comment_node_id"] = (
                json_response[jr].get("payload", {}).get("comment", {}).get("node_id")
            )

        elif event_type == "ReleaseEvent":
            info_dict["tag_name"] = (
                json_response[jr].get("payload", {}).get("release", {}).get("tag_name")
            )
            info_dict["release_node_id"] = (
                json_response[jr].get("payload", {}).get("release", {}).get("node_id")
            )
        events.append(info_dict)
    return events
