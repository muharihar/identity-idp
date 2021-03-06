module AccountReset
  class GrantRequestsAndSendEmails
    def call
      notifications_sent = 0
      AccountResetRequest.where(
        sql_query_for_users_eligible_to_delete_their_accounts,
        tvalue: Time.zone.now - Figaro.env.account_reset_wait_period_days.to_i.days
      ).order('requested_at ASC').each do |arr|
        notifications_sent += 1 if grant_request_and_send_email(arr)
      end
      notifications_sent
    end

    private

    def sql_query_for_users_eligible_to_delete_their_accounts
      <<~SQL
        cancelled_at IS NULL AND
        granted_at IS NULL AND
        requested_at < :tvalue AND
        request_token IS NOT NULL AND
        granted_token IS NULL
      SQL
    end

    def grant_request_and_send_email(arr)
      user = arr.user
      return false unless AccountReset::GrantRequest.new(user).call
      UserMailer.account_reset_granted(user, arr.reload).deliver_later
      true
    end
  end
end
