import os
import sys
import csv
import time
import requests
import requests_cache
requests_cache.install_cache('github_cache')


def group_data_per_server(data):
    """
    Given the rows produced by the fab script, it creates a map of server names
    to puppet details.
    The input looks like this:

    api-1.api,sha:0a64d38e6cf4ede6b43fb39fba048c263ad78498
    api-1.api,time:1481023751
    api-2.api,sha:0a64d38e6cf4ede6b43fb39fba048c263ad78498
    ...

    And results in this:

    {
        'api-1.api': {
            'sha': '0a64d38e6cf4ede6b43fb39fba048c263ad78498',
            'time': '1481023751'
        },
        ...
    }

    """
    server_mapping = {}
    for data_entry in data:
        server_name, metric = data_entry
        puppet_information = server_mapping.get(server_name) or {}
        metric_data = metric.split(':')
        if len(metric_data) == 2:
            metric_name, metric_value = metric_data
            puppet_information[metric_name] = metric_value
            server_mapping[server_name] = puppet_information

    return server_mapping


def enhance_with_release_number(server_mapping):
    """
    Given the mapping generated by group_data_per_server, it calls the GitHub
    API in order to fetch the name of the release tag based on the SHA stored on
    each of the servers.

    Note that this needs a valid GitHub Access token in the environment.
    Because many of the SHAs will be the same, there is caching in place to
    avoid unnecessary calls.
    """
    access_token = os.environ.get('GITHUB_ACCESS_TOKEN')
    if access_token is None:
        raise ValueError("Please set GITHUB_ACCESS_TOKEN in order to continue")

    for server_name, puppet_information in server_mapping.iteritems():
        sha = puppet_information.get('sha')
        url = "https://api.github.com/repos/alphagov/govuk-puppet/git/tags/{}".format(sha)
        response = requests.get(url, headers={'Authorization': "token {}".format(access_token)})
        response_data = response.json()
        puppet_information['release'] = response_data.get(u'tag')
        server_mapping[server_name] = puppet_information

    return server_mapping


def validate_environment(environment):
    """
    Given an environment, makes sure it is valid.
    """
    valid_environments = ['training', 'integration', 'staging', 'production']

    if environment not in valid_environments:
        error = "Invalid environment '{}'. It should be one of: {}".format(
            environment,
            ', '.join(valid_environments)
        )
        raise ValueError(error)


def read_input_file(data_file):
    """
    Reads the input file produced by the fab script
    """
    with open(data_file, 'rb') as f:
        reader = csv.reader(f)
        fab_output = list(reader)

    return fab_output


def print_current_releases(server_mapping, environment):
    print "\n==> The following releases are live in {}\n".format(environment)
    releases = [puppet_information.get('release')
                for server_name, puppet_information in server_mapping.iteritems()]
    for release in set(releases):
        print release


def print_puppet_details_per_server(server_mapping, environment):
    print "\n==> Puppet details per server\n"
    for server_name, puppet_information in server_mapping.iteritems():
        print "{}.{}".format(server_name, environment)
        print "    Current release: {}".format(puppet_information['release'])

        if puppet_information.get('time'):
            time_string = time.ctime(int(puppet_information.get('time')))
        else:
            time_string = 'could not determine, please try again'
        print "    Last puppet run: {}".format(time_string)


if __name__ == '__main__':
    arguments = sys.argv[1:]
    environment = arguments[0]
    data_file = arguments[1]

    validate_environment(environment)
    fab_output = read_input_file(data_file)

    server_mapping = group_data_per_server(fab_output)
    server_mapping = enhance_with_release_number(server_mapping)

    print_current_releases(server_mapping, environment)
    print_puppet_details_per_server(server_mapping, environment)
