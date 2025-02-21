# coding=utf-8
"""Vault UI feature tests."""

__copyright__ = 'Copyright (c) 2020-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import time

from pytest_bdd import (
    parsers,
    scenarios,
    then,
    when,
)

scenarios('../../features/ui/ui_vault.feature')

previous_vault_path = ''


@when(parsers.parse("user browses to data package in {vault}"))
def ui_browse_data_package(browser, vault):
    global previous_vault_path
    link = []
    while len(link) == 0:
        link = browser.links.find_by_partial_text(vault)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('file-browser_next').click()

    browser.find_by_css('.sorting_asc').click()

    research = vault.replace("vault-", "research-")
    data_packages = browser.links.find_by_partial_text(research)
    data_packages.click()
    previous_vault_path = browser.driver.current_url


@when('user submits the data package for publication')
def ui_data_package_submit(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-submit-for-publication').click()


@when('user chooses new publication')
def ui_data_package_choose(browser):
    browser.find_by_css('.action-confirm-data-package-select').click()


@when('user agrees with terms and conditions')
def ui_data_package_agree(browser):
    browser.find_by_id('checkbox-confirm-conditions').check()
    browser.find_by_css('.action-confirm-submit-for-publication').click()


@when('user cancels publication of the data package')
def ui_data_package_cancel(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-cancel-publication').click()


@when('user approves the data package for publication')
def ui_data_package_approve(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-approve-for-publication').click()


@when('user requests depublication of data package')
def ui_data_package_depublish(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-depublish-publication').click()
    browser.find_by_css('.action-confirm-depublish-publication').click()


@when('user requests republication of data package')
def ui_data_package_republish(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-republish-publication').click()
    # And confirm republication
    browser.find_by_css('.action-confirm-republish-publication').click()


@then(parsers.parse('the data package status is "{status}"'))
def ui_data_package_status(browser, status):
    for _i in range(25):
        if browser.is_text_present(status, wait_time=3):
            return True
        browser.reload()

    raise AssertionError()


@then(parsers.parse('provenance log includes "{status}"'))
def ui_provenance_log(browser, status):
    # Check presence of provenance log item.
    # This test can be executed repeatedly as always the n top statuses of the package in research will be checked
    # even though the folder is used several times in a different test run
    browser.find_by_css('.actionlog-icon')[0].click()
    prov_statuses = {"Unpublished": "Secured in vault",
                     "Submitted for publication": "Submitted for publication",
                     "Approved for publication": "Approved for publication",
                     "Published": "Published",
                     "Depublication pending": "Requested depublication",
                     "Depublished": "Depublication",
                     "Republication pending": "Requested republication"}

    for _i in range(25):
        if len(browser.find_by_css('.list-group-item-action')):
            action_log_rows = browser.find_by_css('.list-group-item-action')
            break
        else:
            time.sleep(1)

    for index in range(0, len(prov_statuses)):
        if action_log_rows[index].value.find(prov_statuses[status]) != -1:
            return True


@then('core metadata is visible')
def ui_data_package_core_metadata_is_visible(browser):
    browser.find_by_css('h3.metadata-title', wait_time=5).is_visible()
    browser.find_by_css('h5.metadata-creator', wait_time=5).is_visible()
    browser.find_by_css('div.metadata-description', wait_time=5).is_visible()
    browser.find_by_css('span.metadata-data-classification', wait_time=5).is_visible()
    browser.find_by_css('span.metadata-access', wait_time=5).is_visible()
    browser.find_by_css('hspan.metadata-license', wait_time=5).is_visible()


@when('user clicks metadata button')
def ui_data_package_click_metadata_button(browser):
    browser.find_by_css('button.metadata-form').click()


@then('metadata form is visible')
def ui_data_package_metadata_form_is_visible(browser):
    assert browser.find_by_css('.metadata-form', wait_time=5).is_visible()


@when('user clicks system metadata icon')
def ui_data_package_click_system_metadata_icon(browser):
    browser.find_by_css('.system-metadata', wait_time=5).is_visible()
    browser.find_by_css('.system-metadata-icon').click()


@then('system metadata is visible')
def ui_data_package_system_metadata_is_visible(browser):
    assert browser.find_by_css('.system-metadata', wait_time=5).is_visible()
    assert browser.is_text_present("Data Package Size", wait_time=3)
    assert browser.is_text_present("Data Package Reference", wait_time=3)


@when('user clicks provenance icon')
def ui_data_package_click_provenance_icon(browser):
    browser.find_by_css('.actionlog-icon', wait_time=5).is_visible()
    browser.find_by_css('.actionlog-icon').click()


@then('provenance information is visible')
def ui_data_package_provenance_information_is_visible(browser):
    assert browser.find_by_css('.actionlog', wait_time=5).is_visible()


@when('user clicks action menu to change access')
def ui_data_package_change_vault_access(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-change-vault-access').click()


@then('revoke text is displayed')
def ui_data_package_revoke_message(browser):
    time.sleep(3)
    assert browser.is_text_present('revoke')


@then('grant text is displayed')
def ui_data_package_grant_message(browser):
    time.sleep(3)
    assert browser.is_text_present('grant')


@when("user confirms revoke read permissions")
def ui_data_package_revoke_read_permissions_confirm(browser):
    browser.find_by_css(".action-confirm-revoke-read-permissions").click()


@when("user confirms grant read permissions")
def ui_data_package_grant_read_permissions_confirm(browser):
    browser.find_by_css(".action-confirm-grant-read-permissions").click()


@when('user clicks action menu to copy data package to research')
def ui_data_package_copy_to_research(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-copy-vault-package-to-research').click()


@when('user browses to previous vault package url')
def ui_data_package_browses_previous_url(browser):
    if len(previous_vault_path):
        browser.visit(previous_vault_path)
    else:
        assert False


@then('contents of folder are shown')
def ui_data_package_contents(browser):
    assert browser.is_text_present('yoda-metadata')
    assert browser.is_text_present('original')


@then('user does not have access to folder')
def ui_data_package_no_access(browser):
    assert browser.is_text_present('This vault space path does not exist')


@when(parsers.parse("user chooses research folder corresponding to {vault}"))
def ui_browse_research_to_copy_data_package_to(browser, vault):
    research = vault.replace("vault-", "research-")
    href = "?dir=%2F{}".format(research)
    link = []
    while len(link) == 0:
        link = browser.links.find_by_href(href)
        if len(link) > 0:
            link.click()
        else:
            browser.find_by_id('folder-select-browser_next').click()


@when('user presses copy package button')
def ui_user_presses_copy_package_button(browser):
    browser.find_by_id('btn-copy-package').click()


@then('data package is copied to research area')
def ui_data_package_is_copied_to_research(browser):
    # TODO
    pass


@when('user clicks clicks action menu to check compliance')
def ui_data_package_check_compliance(browser):
    browser.find_by_id('actionMenu').click()
    browser.find_by_css('a.action-check-for-unpreservable-files').click()


@when('user chooses policy')
def ui_data_package_choose_policy(browser):
    browser.find_by_id('file-formats-list').click()
    browser.find_option_by_value('DANS').click()


@then('compliance result is presented')
def ui_data_package_compliance_is_presented(browser):
    assert browser.find_by_css('p.help')


@when('user clicks go to research')
def ui_data_package_go_to_research(browser):
    browser.find_by_css('.btn-go-to-research').click()


@then(parsers.parse("the research space of {vault} is shown"))
def ui_vault_research_space(browser, vault):
    research = vault.replace("vault-", "research-")
    assert browser.is_text_present(research, wait_time=3)
