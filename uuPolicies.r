# \file
# \brief iRODS policies for Yoda (changes to core.re)
# \author Ton Smeele
# \copyright Copyright (c) 2015, Utrecht university. All rights reserved
# \license GPLv3, see LICENSE
#
#test {
#	acPreProcForExecCmd("foo");
#}

# \brief preProcForExecCmd
# 			limit the use of OS callouts to a user group "priv-execcmd-all"
#
# \param[in]		cmd  name of executable
#
acPreProcForExecCmd(*cmd, *args, *addr, *hint) {
	*accessAllowed = false;
	foreach (*rows in SELECT USER_GROUP_NAME WHERE USER_NAME='$userNameClient'
		             AND USER_ZONE='$rodsZoneClient') {
		msiGetValByKey(*rows, "USER_GROUP_NAME", *group);
		if (*group == "priv-execcmd-all") {
			*accessAllowed = true;
		}
	}
	if (*accessAllowed == false) {
		cut;
		msiOprDisallowed;
	}
}

# acCreateUserZoneCollections extended to also set inherit on the home coll
# this is needed for groupcollections to allow users to share objects 
acCreateUserZoneCollections {
	uuGetUserType($otherUserName, *type);
	if (*type != "rodsgroup" || !($otherUserName like "read-*")) {
		acCreateCollByAdmin("/"++$rodsZoneProxy++"/home", $otherUserName);
		acCreateCollByAdmin("/"++$rodsZoneProxy++"/trash/home", $otherUserName);
		msiSetACL("default", "admin:inherit", $otherUserName, "/"++$rodsZoneProxy++"/home/"++$otherUserName);
	}
}

#input null
#output ruleExecOut
