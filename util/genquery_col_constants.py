# -*- coding: utf-8 -*-
"""GenQuery column constants

   Adapted from ./lib/core/include/rodsGenQuery.h in main iRODS repository."""

__copyright__ = 'Copyright (c) 2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

# R_DATA_MAIN
COL_D_DATA_ID = 401
COL_D_COLL_ID = 402
COL_DATA_NAME = 403
COL_DATA_REPL_NUM = 404
COL_DATA_VERSION = 405
COL_DATA_TYPE_NAME = 406
COL_DATA_SIZE = 407
COL_D_RESC_NAME = 409
COL_D_DATA_PATH = 410
COL_D_OWNER_NAME = 411
COL_D_OWNER_ZONE = 412
COL_D_REPL_STATUS = 413
COL_D_DATA_STATUS = 414
COL_D_DATA_CHECKSUM = 415
COL_D_EXPIRY = 416
COL_D_MAP_ID = 417
COL_D_COMMENTS = 418
COL_D_CREATE_TIME = 419
COL_D_MODIFY_TIME = 420
COL_DATA_MODE = 421
COL_D_RESC_HIER = 422
COL_D_RESC_ID = 423

# R_COLL_MAIN
COL_COLL_ID = 500
COL_COLL_NAME = 501
COL_COLL_PARENT_NAME = 502
COL_COLL_OWNER_NAME = 503
COL_COLL_OWNER_ZONE = 504
COL_COLL_MAP_ID = 505
COL_COLL_INHERITANCE = 506
COL_COLL_COMMENTS = 507
COL_COLL_CREATE_TIME = 508
COL_COLL_MODIFY_TIME = 509
COL_COLL_TYPE = 510
COL_COLL_INFO1 = 511
COL_COLL_INFO2 = 512

# R_RESC_MAIN
COL_R_RESC_ID = 301
COL_R_RESC_NAME = 302
COL_R_ZONE_NAME = 303
COL_R_TYPE_NAME = 304
COL_R_CLASS_NAME = 305
COL_R_LOC = 306
COL_R_VAULT_PATH = 307
COL_R_FREE_SPACE = 308
COL_R_RESC_INFO  = 309
COL_R_RESC_COMMENT = 310
COL_R_CREATE_TIME = 311
COL_R_MODIFY_TIME = 312
COL_R_RESC_STATUS = 313
COL_R_FREE_SPACE_TIME = 314
COL_R_RESC_CHILDREN = 315
COL_R_RESC_CONTEXT = 316
COL_R_RESC_PARENT = 317
COL_R_RESC_PARENT_CONTEXT = 318

# R_USER_MAIN
COL_USER_ID = 201
COL_USER_NAME = 202
COL_USER_TYPE = 203
COL_USER_ZONE = 204
COL_USER_INFO = 206
COL_USER_COMMENT = 207
COL_USER_CREATE_TIME = 208
COL_USER_MODIFY_TIME = 209
COL_USER_GROUP_ID = 900
COL_USER_GROUP_NAME = 901

# Metadata for data objects
COL_META_DATA_ATTR_NAME = 600
COL_META_DATA_ATTR_VALUE = 601
COL_META_DATA_ATTR_UNITS = 602
COL_META_DATA_ATTR_ID = 603
COL_META_DATA_CREATE_TIME = 604
COL_META_DATA_MODIFY_TIME = 605

# Metadata for collections
COL_META_COLL_ATTR_NAME = 610
COL_META_COLL_ATTR_VALUE = 611
COL_META_COLL_ATTR_UNITS = 612
COL_META_COLL_ATTR_ID = 613
COL_META_COLL_CREATE_TIME = 614
COL_META_COLL_MODIFY_TIME = 615

# Metadata for resources
COL_META_RESC_ATTR_NAME = 630
COL_META_RESC_ATTR_VALUE = 631
COL_META_RESC_ATTR_UNITS = 632
COL_META_RESC_ATTR_ID = 633
COL_META_RESC_CREATE_TIME = 634
COL_META_RESC_MODIFY_TIME = 635

# Metadata for users
COL_META_USER_ATTR_NAME = 640
COL_META_USER_ATTR_VALUE = 641
COL_META_USER_ATTR_UNITS = 642
COL_META_USER_ATTR_ID = 643
COL_META_USER_CREATE_TIME = 644
COL_META_USER_MODIFY_TIME = 645
