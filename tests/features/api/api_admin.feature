@api
Feature: Admin API

    Scenario Outline: User has admin access
        Given user <user> is authenticated
        And the admin has access API is queried
        Then the response status code is "200"
        And the response result is "True"

        Examples:
            | user                |
            | technicaladmin      |
            | functionaladminpriv |


    Scenario Outline: User has NO admin access
        Given user <user> is authenticated
        And the admin has access API is queried
        Then the response status code is "200"
        And the response result is "False"

        Examples:
            | user                |
            | researcher          |
