import logging as log

from . import gitlab

GET, POST, PUT = gitlab.GET, gitlab.POST, gitlab.PUT


class Approvals(gitlab.Resource):
    """Approval info for a MergeRequest."""

    def refetch_info(self):
        gitlab_version = self._api.version()
        if gitlab_version.release >= (9, 2, 2):
            approver_url = '/projects/{0.project_id}/merge_requests/{0.iid}/approvals'.format(self)
        else:
            # GitLab botched the v4 api before 9.2.3
            approver_url = '/projects/{0.project_id}/merge_requests/{0.id}/approvals'.format(self)

        self._info = self._api.call(GET(approver_url))

    @property
    def iid(self):
        return self.info['iid']

    @property
    def project_id(self):
        return self.info['project_id']

    @property
    def approvals_left(self):
        return self.info['approvals_left'] or 0

    @property
    def sufficient(self):
        return not self.info['approvals_left']

    @property
    def approver_usernames(self):
        return [who['user']['username'] for who in self.info['approved_by']]

    @property
    def approver_ids(self):
        """Return the uids of the approvers."""
        return [who['user']['id'] for who in self.info['approved_by']]

    @property
    def approval_url(self):
        if self._api.version().release >= (9, 2, 2):
            return '/projects/{0.project_id}/merge_requests/{0.iid}/approve'.format(self)

        # GitLab botched the v4 api before 9.2.3
        return '/projects/{0.project_id}/merge_requests/{0.id}/approve'.format(self)

    def reapprove_as_approvers(self):
        """Impersonates the approvers and re-approves the merge_request as them.

        The idea is that we want to get the approvers, push the rebased branch
        (which may invalidate approvals, depending on GitLab settings) and then
        restore the approval status.
        """
        for uid in self.approver_ids:
            log.info('Approving as user %d', uid)
            self._api.call(POST(self.approval_url), sudo=uid)

    def reapprove_as_marge(self):
        """Re-approves as the marge-bot user.

        The idea is that we want to get the approvers, push the rebased branch
        (which may invalidate approvals, depending on GitLab settings) and then
        restore the approval status.
        """
        log.info('Approving as marge')
        self._api.call(POST(self.approval_url))
