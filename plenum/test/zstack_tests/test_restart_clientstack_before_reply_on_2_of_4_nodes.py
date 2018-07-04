import types

import pytest

from plenum.test.helper import sdk_send_random_and_check
from plenum.test.node_catchup.helper import ensure_all_nodes_have_same_data


@pytest.mark.skip(reason="Too much request. Needs for checking future implementation")
def test_restart_clientstack_before_reply_on_2_of_4_nodes(looper,
                                                          txnPoolNodeSet,
                                                          sdk_pool_handle,
                                                          sdk_wallet_steward):
    orig_send_reply = txnPoolNodeSet[0].sendReplyToClient
    def send_after_restart(self, reply, reqKey):
        self.restart_clientstack()
        orig_send_reply(reply, reqKey)

    def patch_sendReplyToClient():
        for node in txnPoolNodeSet[:2]:
            node.sendReplyToClient = types.MethodType(send_after_restart,
                                                      node)
    def revert_origin_back():
        for node in txnPoolNodeSet:
            node.sendReplyToClient = types.MethodType(orig_send_reply,
                                                      node)

    patch_sendReplyToClient()
    sdk_send_random_and_check(looper,
                              txnPoolNodeSet,
                              sdk_pool_handle,
                              sdk_wallet_steward,
                              1)
    ensure_all_nodes_have_same_data(looper, txnPoolNodeSet)
    revert_origin_back()