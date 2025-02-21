# -*- coding: utf-8 -*-
"""JSON metadata handling."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import re
from collections import OrderedDict
from datetime import datetime

import genquery
import irods_types
from deepdiff import DeepDiff

import provenance
import publication
import schema as schema_
import vault
from util import *

__all__ = ['rule_meta_validate',
           'api_meta_remove',
           'api_meta_clone_file',
           'rule_meta_modified_post',
           'rule_meta_datamanager_vault_ingest',
           'rule_meta_collection_has_cloneable_metadata',
           'rule_get_latest_vault_metadata_path']


def metadata_get_links(metadata):
    if 'links' not in metadata or type(metadata['links']) is not list:
        return []
    return filter(lambda x: type(x) in (dict, OrderedDict)
                  and 'rel' in x
                  and 'href' in x
                  and type(x['rel']) is str
                  and type(x['href']) is str,
                  metadata['links'])


def metadata_get_schema_id(metadata):
    desc = filter(lambda x: x['rel'] == 'describedby', metadata_get_links(metadata))
    if len(desc) > 0:
        return desc[0]['href']


def metadata_set_schema_id(metadata, schema_id):
    other_links = filter(lambda x: x['rel'] != 'describedby', metadata_get_links(metadata))

    metadata['links'] = [OrderedDict([
        ['rel',  'describedby'],
        ['href', schema_id]
    ])] + other_links


def get_json_metadata_errors(callback,
                             metadata_path,
                             metadata=None,
                             schema=None,
                             ignore_required=False):
    """
    Validate JSON metadata, and return a list of errors, if any.

    The path to the JSON object must be provided, so that the active schema path
    can be derived. Optionally, a pre-parsed JSON object may be provided in
    'metadata'.

    The checked schema is, by default, the active schema for the given metadata path,
    however it can be overridden by providing a parsed JSON schema as an argument.

    This will throw exceptions on missing metadata / schema files and invalid
    JSON formats.

    :param callback:        Combined type of a callback and rei struct
    :param metadata_path:   Path to the JSON object
    :param metadata:        Pre-parsed JSON object
    :param schema:          Schema to check against
    :param ignore_required: Ignore required fields

    :returns: List of errors in JSON object
    """
    if schema is None:
        schema = schema_.get_active_schema(callback, metadata_path)

    if metadata is None:
        metadata = jsonutil.read(callback, metadata_path)

    # Perform validation and filter errors.
    # Validation is handed to a Python 3 interpreter to validate with the Draft201909 validator.
    # This can be removed when we can use Python 3 in the ruleset (iRODS 4.3.x).
    # validator = jsonschema.Draft7Validator(schema)
    #
    # errors = validator.iter_errors(metadata)
    #
    # if ignore_required:
    #     errors = filter(lambda e: e.validator not in ['required', 'dependencies'], errors)
    #
    # def transform_error(e):
    #     """Turn a ValidationError into a data structure for the frontend."""
    #     return {'message':     e.message,
    #             'path':        list(e.path),
    #             'schema_path': list(e.schema_path),
    #             'validator':   e.validator}
    #
    # return map(transform_error, errors)

    # Can't serialize OrderedDict, so transform to dicts.
    schema = json.loads(json.dumps(schema))
    metadata = json.loads(json.dumps(metadata))

    # Create gateway to Python 3.8.
    import execnet
    gw = execnet.makegateway("popen//python=" + config.python3_interpreter)

    channel = gw.remote_exec("""
        import jsonschema
        errors = []
        while 1:
            schema, metadata, ignore_required = channel.receive()
            if schema is None:
                break

            # Perform validation and filter errors.
            validator = jsonschema.Draft201909Validator(schema)
            errors = validator.iter_errors(metadata)

            if ignore_required:
                errors = filter(lambda e: e.validator not in ['required', 'dependencies'], errors)

            def transform_error(e):
                return {'message':     e.message,
                        'path':        list(e.path),
                        'schema_path': list(e.schema_path),
                        'validator':   e.validator}

            errors = list(map(transform_error, errors))
        channel.send(errors)
    """)

    channel.send((schema, metadata, ignore_required))
    channel.send((None, None, None))
    errors = channel.receive()

    # Log metadata errors.
    for error in errors:
        log.write(callback, error)

    return errors


def is_json_metadata_valid(callback,
                           metadata_path,
                           metadata=None,
                           ignore_required=False):
    """
    Check if json metadata contains no errors.

    Argument 'metadata' may contain a preparsed JSON document, otherwise it
    is loaded from the provided path.

    :param callback:        Combined type of a callback and rei struct
    :param metadata_path:   Path to the JSON object
    :param metadata:        Pre-parsed JSON object
    :param ignore_required: Ignore required fields

    :returns: Boolean indicating if JSON metadata us valid
    """
    try:
        return len(get_json_metadata_errors(callback,
                                            metadata_path,
                                            metadata=metadata,
                                            ignore_required=ignore_required)) == 0
    except error.UUError:
        # File may be missing or not valid JSON.
        return False


def get_collection_metadata_path(ctx, coll):
    """
    Check if a collection has a JSON metadata file and provide its path, if any.

    :param ctx:  Combined type of a callback and rei struct
    :param coll: Path of collection to check for metadata

    :returns: String with path to metadata file
    """
    path = '{}/{}'.format(coll, constants.IIJSONMETADATA)
    if data_object.exists(ctx, path):
        return path

    return None


def get_latest_vault_metadata_path(ctx, vault_pkg_coll):
    """
    Get the latest vault metadata JSON file.

    :param ctx:            Combined type of a callback and rei struct
    :param vault_pkg_coll: Vault package collection

    :returns: string -- Metadata JSON path
    """
    name = None

    iter = genquery.row_iterator(
        "DATA_NAME",
        "COLL_NAME = '{}' AND DATA_NAME like 'yoda-metadata[%].json'".format(vault_pkg_coll),
        genquery.AS_LIST, ctx)

    for row in iter:
        data_name = row[0]
        if name is None or (name < data_name and len(name) <= len(data_name)):
            name = data_name

    return None if name is None else '{}/{}'.format(vault_pkg_coll, name)


rule_get_latest_vault_metadata_path = (
    rule.make(inputs=[0], outputs=[1],
              transform=lambda x: x if type(x) is str else '')
             (get_latest_vault_metadata_path))


def rule_meta_validate(rule_args, callback, rei):
    """Validate JSON metadata file."""
    json_path = rule_args[0]

    try:
        errs = get_json_metadata_errors(callback, json_path)
    except error.UUError as e:
        errs = [{'message': str(e)}]

    if len(errs):
        rule_args[1] = '1'
        rule_args[2] = 'metadata validation failed:\n' + '\n'.join([err['message'] for err in errs])
    else:
        rule_args[1] = '0'
        rule_args[2] = 'metadata validated'


def collection_has_cloneable_metadata(callback, coll):
    """
    Check if a collection has metadata, and validate it.

    This always ignores 'required' schema attributes, since metadata can
    only be cloned in the research area.

    :param callback: Combined type of a callback and rei struct
    :param coll:     Path of collection to check for cloneable metadata

    :returns: String with the parent metadata_path on success, or False otherwise.
    """
    path = get_collection_metadata_path(callback, coll)

    if path is None:
        return False

    if path.endswith('.json'):
        if is_json_metadata_valid(callback, path, ignore_required=True):
            return path

    return False


rule_meta_collection_has_cloneable_metadata = (
    rule.make(inputs=[0], outputs=[1],
              transform=lambda x: x if type(x) is str else '')
             (collection_has_cloneable_metadata))


@api.make()
def api_meta_remove(ctx, coll):
    """Remove a collection's metadata JSON, if it exist."""
    log.write(ctx, 'Remove metadata of coll {}'.format(coll))

    try:
        data_object.remove(ctx, '{}/{}'.format(coll, constants.IIJSONMETADATA))
    except error.UUError:
        # ignore non-existent files.
        # (this may also fail for other reasons, but we can't distinguish them)
        pass


@api.make()
def api_meta_clone_file(ctx, target_coll):
    """Clone a metadata file from a parent collection to a subcollection.

    :param ctx:         Combined type of a callback and rei struct
    :param target_coll: Target collection (where the metadata is copied to)

    :returns: None

    :raises Error: The metadata file could not be copied
    """
    source_coll = pathutil.chop(target_coll)[0]  # = parent collection
    source_data = get_collection_metadata_path(ctx, source_coll)

    if source_data.endswith('.json'):
        target_data = '{}/{}'.format(target_coll, constants.IIJSONMETADATA)
    else:
        # No metadata to clone? Abort.
        return

    try:
        data_object.copy(ctx, source_data, target_data)
    except msi.Error as e:
        raise api.Error('copy_failed', 'The metadata file could not be copied', str(e))


# Functions that deal with ingesting metadata into AVUs {{{

def ingest_metadata_research(ctx, path):
    """Validate JSON metadata (without requiredness) and ingests as AVUs in the research space."""
    coll, data = pathutil.chop(path)

    try:
        metadata = jsonutil.read(ctx, path)
    except error.UUError:
        log.write(ctx, 'ingest_metadata_research failed: Could not read {} as JSON'.format(path))
        return

    if not is_json_metadata_valid(ctx, path, metadata, ignore_required=True):
        log.write(ctx, 'ingest_metadata_research failed: {} is invalid'.format(path))
        return

    # Note: We do not set a $id in research space: this would trigger jsonavu
    # validation, which does not respect our wish to ignore required
    # properties in the research area.

    # Replace all metadata under this namespace.
    jsonutil.set_on_object(ctx, coll, "collection",
                           constants.UUUSERMETADATAROOT,
                           jsonutil.dump(metadata))


def ingest_metadata_deposit(ctx, path):
    """Validate JSON metadata (without requiredness) and ingests as AVUs in the deposit space."""
    coll, data = pathutil.chop(path)

    try:
        metadata = jsonutil.read(ctx, path)
    except error.UUError:
        log.write(ctx, 'ingest_metadata_deposit failed: Could not read {} as JSON'.format(path))
        return

    if not is_json_metadata_valid(ctx, path, metadata, ignore_required=True):
        log.write(ctx, 'ingest_metadata_deposit failed: {} is invalid'.format(path))
        return

    # Set Title and Data Access Restriction of deposit as AVU.
    if 'Title' in metadata:
        avu.associate_to_coll(ctx, coll, 'Title', metadata['Title'])
    if 'Data_Access_Restriction' in metadata:
        avu.associate_to_coll(ctx, coll, 'Data_Access_Restriction', metadata['Data_Access_Restriction'])


def ingest_metadata_staging(ctx, path):
    """Set cronjob metadata flag and triggers vault ingest."""
    ret = msi.string_2_key_val_pair(ctx,
                                    '{}{}{}'.format(constants.UUORGMETADATAPREFIX,
                                                    'cronjob_vault_ingest=',
                                                    constants.CRONJOB_STATE['PENDING']),
                                    irods_types.BytesBuf())

    msi.set_key_value_pairs_to_obj(ctx, ret['arguments'][1], path, '-d')

    # Note: Validation is triggered via ExecCmd in rule_meta_datamanager_vault_ingest.
    #
    # msiExecCmd is currently not usable from Python rule engine:
    # https://github.com/irods/irods_rule_engine_plugin_python/issues/11
    # msi.exec_cmd(ctx, "admin-vaultingest.sh", user.full_name(ctx), "", "", "", irods_types.ExecCmdOut())
    ctx.iiAdminVaultIngest()


def update_index_metadata(ctx, path, metadata, creation_time, data_package):
    """Update the index attributes for JSON metadata."""
    msi.coll_create(ctx, path, "", irods_types.BytesBuf())
    ctx.msi_rmw_avu('-C', path, '%', '%', constants.UUFLATINDEX)
    avu_op = "add"
    avu_unit = constants.UUFLATINDEX
    metadata_operations = {
        "entity_name": path,
        "entity_type": "collection",
        "operations": []
    }

    for creator in metadata['Creator']:
        name = creator['Name']
        if 'Given_Name' in name and 'Family_Name' in name:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Creator",
                "value": name['Given_Name'] + ' ' + name['Family_Name'],
                "units": avu_unit
            })
        if 'Owner_Role' in creator:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Owner_Role",
                "value": creator['Owner_Role'],
                "units": avu_unit
            })

    if 'Contributor' in metadata:
        for contributor in metadata['Contributor']:
            if 'Name' in contributor:
                name = contributor['Name']
                if 'Given_Name' in name and 'Family_Name' in name:
                    metadata_operations['operations'].append({
                        "operation": avu_op,
                        "attribute": "Contributor",
                        "value": name['Given_Name'] + ' ' + name['Family_Name'],
                        "units": avu_unit
                    })

    if 'Tag' in metadata:
        for tag in metadata['Tag']:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Tag",
                "value": tag,
                "units": avu_unit
            })

    extend_operations = [
        {
            "operation": avu_op,
            "attribute": "Title",
            "value": metadata['Title'],
            "units": avu_unit
        },
        {
            "operation": avu_op,
            "attribute": "Description",
            "value": metadata['Description'],
            "units": avu_unit
        },
        {
            "operation": avu_op,
            "attribute": "Data_Access_Restriction",
            "value": metadata['Data_Access_Restriction'],
            "units": avu_unit
        },
        {
            "operation": avu_op,
            "attribute": "Creation_Time",
            "value": creation_time,
            "units": avu_unit
        },
        {
            "operation": avu_op,
            "attribute": "Creation_Year",
            "value": str(datetime.fromtimestamp(int(creation_time)).year),
            "units": avu_unit
        }]

    metadata_operations['operations'].extend(extend_operations)

    if 'Research_Group' in metadata:
        metadata_operations['operations'].append({
            "operation": avu_op,
            "attribute": "Research_Group",
            "value": metadata['Research_Group'],
            "units": avu_unit
        })
    if 'Collection_Name' in metadata:
        metadata_operations['operations'].append({
            "operation": avu_op,
            "attribute": "Collection_Name",
            "value": metadata['Collection_Name'],
            "units": avu_unit
        })
    if 'Collected' in metadata:
        if 'Start_Date' in metadata['Collected']:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Collected_Start_Year",
                "value": metadata['Collected']['Start_Date'][:4],
                "units": avu_unit
            })
        if 'End_Date' in metadata['Collected']:
            metadata_operations['operations'].append({
                "operation": avu_op,
                "attribute": "Collected_End_Year",
                "value": metadata['Collected']['End_Date'][:4],
                "units": avu_unit
            })

    if 'GeoLocation' in metadata:
        for geoLocation in metadata['GeoLocation']:
            if 'Description_Spatial' in geoLocation:
                metadata_operations['operations'].append({
                    "operation": avu_op,
                    "attribute": "Description_Spatial",
                    "value": geoLocation['Description_Spatial'],
                    "units": avu_unit
                })

    if config.enable_data_package_reference:
        metadata_operations['operations'].append({
            "operation": "add",
            "attribute": "Data_Package_Reference",
            "value": data_package,
            "units": avu_unit
        })

    if avu.apply_atomic_operations(ctx, metadata_operations):
        log.write(ctx, 'update_index_metadata: Metadata index update successful on path {}'.format(path))
    else:
        log.write(ctx, 'update_index_metadata: Metadata index update unsuccessful on path {}'.format(path))


def ingest_metadata_vault(ctx, path):
    """Ingest (pre-validated) JSON metadata in the vault."""
    # The JSON metadata file has just landed in the vault, required validation /
    # logging / provenance has already taken place.

    # Read the metadata file and apply it as AVUs.

    coll = pathutil.chop(path)[0]

    try:
        metadata = jsonutil.read(ctx, path)
    except error.UUError:
        log.write(ctx, 'ingest_metadata_vault failed: Could not read {} as JSON'.format(path))
        return

    # Get creation time.
    creation_time = ""
    iter = genquery.row_iterator(
        "COLL_CREATE_TIME",
        "COLL_NAME = '%s'" % (coll),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        creation_time = str(int(row[0]))

    # Get Data Package Reference.
    data_package = ""
    if config.enable_data_package_reference:
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '{}' AND META_COLL_ATTR_NAME = '{}'".format(coll, constants.DATA_PACKAGE_REFERENCE),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            data_package = row[0]

    # Update flat index metadata for OpenSearch.
    if config.enable_open_search and group.exists(ctx, coll.split("/")[3].replace("vault-", "deposit-", 1)):
        update_index_metadata(ctx, coll + "/index", metadata, creation_time, data_package)

    # Replace all metadata under this namespace.
    jsonutil.set_on_object(ctx, coll, "collection",
                           constants.UUUSERMETADATAROOT,
                           jsonutil.dump(metadata))

# }}}


@rule.make()
def rule_meta_modified_post(ctx, path, user, zone):
    if re.match('^/{}/home/datamanager-[^/]+/vault-[^/]+/.*'.format(zone), path):
        ingest_metadata_staging(ctx, path)
    elif re.match('^/{}/home/vault-[^/]+/.*'.format(zone), path):
        ingest_metadata_vault(ctx, path)
        vault.update_archive(ctx, path)
    elif re.match('^/{}/home/research-[^/]+/.*'.format(zone), path):
        ingest_metadata_research(ctx, path)
    elif re.match('^/{}/home/deposit-[^/]+/.*'.format(zone), path):
        ingest_metadata_deposit(ctx, path)


def rule_meta_datamanager_vault_ingest(rule_args, callback, rei):
    """Ingest changes to metadata into the vault."""
    # This rule is called via ExecCmd during a policy rule
    # (ingest_metadata_staging), with as an argument the path to a metadata
    # JSON in a staging area (a location in a datamanager home collection).
    #
    # As user rods, we validate the metadata, and if successful, copy it, timestamped, into the vault.
    # Necessary log & provenance info is recorded, and a publication update is triggered if necessary.
    # An AVU update is triggered via policy during the copy action.
    ctx = rule.Context(callback, rei)
    json_path = rule_args[0]
    rule_args[1:3] = 'UnknownError', ''

    # FIXME: this kvp issue needs to be addressed on a wider scale.
    if json_path.find('++++') != -1:
        return

    def set_result(msg_short, msg_long):
        rule_args[1:3] = msg_short, msg_long
        if msg_short != 'Success':
            log.write(ctx, 'rule_meta_datamanager_vault_ingest failed: {}'.format(msg_long))
        return

    # Parse path to JSON object.
    m = re.match('^/([^/]+)/home/(datamanager-[^/]+)/(vault-[^/]+)/(.+)/{}$'.format(constants.IIJSONMETADATA), json_path)
    if not m:
        set_result('JsonPathInvalid', 'Json staging path <{}> invalid'.format(json_path))
        return

    zone, dm_group, vault_group, vault_subpath = m.groups()
    dm_path = '/{}/home/{}'.format(zone, dm_group)

    # Make sure the vault package coll exists.
    vault_path = '/{}/home/{}'.format(zone, vault_group)
    vault_pkg_path = '{}/{}'.format(vault_path, vault_subpath)

    if not collection.exists(ctx, vault_pkg_path):
        set_result('JsonPathInvalid', 'Vault path <{}> does not exist'.format(vault_pkg_path))
        return

    actor = data_object.owner(ctx, json_path)
    if actor is None:
        set_result('JsonPathInvalid', 'Json object <{}> does not exist'.format(json_path))
        return
    actor = actor[0]  # Discard zone name.

    # Make sure rods has access to the json file.
    client_full_name = user.full_name(ctx)

    # Get the metadata before the ingest
    previous_metadata = get_latest_vault_metadata_path(ctx, vault_pkg_path)
    prev_json = jsonutil.read(ctx, previous_metadata)
    prev_json_data = json.loads(json.dumps(prev_json))

    try:
        ret = msi.check_access(ctx, json_path, 'modify object', irods_types.BytesBuf())
        if ret['arguments'][2] != b'\x01':
            msi.set_acl(ctx, 'default', 'admin:own', client_full_name, json_path)
    except error.UUError:
        set_result('AccessError', 'Couldn\'t grant access to json metadata file')
        return

    # Determine destination filename.
    # FIXME - TOCTOU: should do this in a loop around msi.data_obj_copy instead.
    ret = msi.get_icat_time(ctx, '', 'unix')
    timestamp = ret['arguments'][0].lstrip('0')

    json_name, json_ext = constants.IIJSONMETADATA.split('.', 1)
    dest = '{}/{}[{}].{}'.format(vault_pkg_path, json_name, timestamp, json_ext)
    i = 0
    while data_object.exists(ctx, dest):
        i += 1
        dest = '{}/{}[{}][{}].{}'.format(vault_pkg_path, json_name, timestamp, i, json_ext)

    # Validate metadata.
    # FIXME - TOCTOU: might fix by reading JSON only once, and validating and writing to vault from that.
    ret = callback.rule_meta_validate(json_path, '', '')
    invalid = ret['arguments'][1]
    if invalid == '1':
        set_result('FailedToValidateJSON', ret['arguments'][2])
        return

    # Copy the file, with its ACLs.
    try:
        # Note: This copy triggers metadata/AVU ingestion via policy.
        msi.data_obj_copy(ctx, json_path, dest, 'destRescName={}++++verifyChksum='.format(config.resource_vault), irods_types.BytesBuf())
    except error.UUError:
        set_result('FailedToCopyJSON', 'Couldn\'t copy json metadata file from <{}> to <{}>'
                   .format(json_path, dest))
        return

    # Get the metadata after the ingest
    latest_metadata = get_latest_vault_metadata_path(ctx, vault_pkg_path)
    current_json = jsonutil.read(ctx, latest_metadata)
    current_json_data = json.loads(json.dumps(current_json))

    try:
        callback.iiCopyACLsFromParent(dest, 'default')
    except Exception:
        set_result('FailedToSetACLs', 'Failed to set vault permissions on <{}>'.format(dest))
        return

    # Log the difference between the metadata before and after the ingest
    try:
        meta_diff = DeepDiff(prev_json_data, current_json_data)
        item_list = {}
        for i in meta_diff:
            action = i.split('_')[-1]
            item_list[action] = []
            if i.startswith('dictionary'):
                keys = meta_diff[i]
            else:
                keys = meta_diff[i].keys()
            if keys:
                for item in keys:
                    m = re.match("root\['(.*?)'\]", item)
                    if m:
                        item_list[action].append(m.group(1).replace('_', ' '))

        for item in item_list:
            if len(item_list[item]) < 5:
                list_of_changes = ', '.join(item_list[item])
                provenance.log_action(ctx, actor, vault_pkg_path, '{} metadata: {}'.format(item.replace('changed', 'modified'), list_of_changes))
            else:
                list_of_changes = ', '.join(item_list[item][:4])
                provenance.log_action(ctx, actor, vault_pkg_path, '{} metadata: {} and more'.format(item.replace('changed', 'modified'), list_of_changes))
    except Exception:
        # Log provenance without the differences
        provenance.log_action(ctx, actor, vault_pkg_path, 'modified metadata')

    # Write license file.
    vault.vault_write_license(ctx, vault_pkg_path)

    # Cleanup staging area.
    try:
        data_object.remove(ctx, json_path, force=True)
    except Exception:
        set_result('FailedToRemoveDatamanagerMetadata', 'Failed to remove <{}>'.format(json_path))
        return

    stage_coll = '/{}/home/{}/{}'.format(zone, dm_group, vault_group)
    if collection.empty(ctx, stage_coll):
        try:
            # We may or may not have delete access already.
            msi.set_acl(ctx, 'recursive', 'admin:own', client_full_name, dm_path)
        except error.UUError:
            pass
        try:
            msi.rm_coll(ctx, stage_coll, 'forceFlag=', irods_types.BytesBuf())
        except error.UUError:
            set_result('FailedToRemoveColl', 'Failed to remove <{}>'.format(stage_coll))
            return

    # Update publication if package is published.
    status = vault.get_coll_vault_status(ctx, vault_pkg_path)
    if status is constants.vault_package_state.PUBLISHED:
        # Add publication update status to vault package.
        # Also used in frontend to check if vault package metadata update is pending.
        s = constants.UUORGMETADATAPREFIX + "cronjob_publication_update=" + constants.CRONJOB_STATE['PENDING']
        try:
            ret = msi.string_2_key_val_pair(ctx, s, irods_types.BytesBuf())
            kvp = ret['arguments'][1]
            msi.associate_key_value_pairs_to_obj(ctx, kvp, vault_pkg_path, '-C')
            publication.set_update_publication_state(ctx, vault_pkg_path)
        except Exception:
            set_result('FailedToSetPublicationUpdateStatus',
                       'Failed to set publication update status on <{}>'.format(vault_pkg_path))
            return

    set_result('Success', '')


def copy_user_metadata(ctx, source, target):
    """
    Copy the user metadata (AVUs) of a collection to another collection.

    This only copies user metadata, so it ignores system metadata.

    :param ctx:    Combined type of a callback and rei struct
    :param source: Path of source collection.
    :param target: Path of target collection.
    """
    try:
        # Retrieve all AVUs inside source collection.
        user_metadata = list(avu.inside_coll(ctx, source, recursive=True))

        # Group AVUs by entity and filter system metadata.
        grouped_user_metadata = {}
        for path, type, attribute, value, unit in user_metadata:
            if not attribute.startswith(constants.UUORGMETADATAPREFIX) and unit != constants.UUFLATINDEX and not unit.startswith(constants.UUUSERMETADATAROOT + '_'):
                grouped_user_metadata.setdefault(path, {"type": type, "avus": []})
                grouped_user_metadata[path]["avus"].append((attribute, value, unit))

        # Generate metadata operations.
        for path, item in grouped_user_metadata.items():
            operations = {
                "entity_name": path.replace(source, "{}/original".format(target), 1),
                "entity_type": item["type"],
                "operations": []
            }

            for attribute, value, unit in item["avus"]:
                operations["operations"].append(
                    {
                        "operation": "add",
                        "attribute": attribute,
                        "value": value,
                        "units": unit
                    }
                )

            # Apply metadata operations.
            if not avu.apply_atomic_operations(ctx, operations):
                log.write(ctx, "copy_user_metadata: failed to copy user metadata for <{}>".format(path))

        log.write(ctx, "copy_user_metadata: copied user metadata from <{}> to <{}/original>".format(source, target))
    except Exception:
        log.write(ctx, "copy_user_metadata: failed to copy user metadata from <{}> to <{}/original>".format(source, target))
