class AnonymousUser
  def uuid
    'anonymous-uuid'
  end

  def second_factor_locked_at
    nil
  end

  def phone_configurations
    []
  end

  def phone
    nil
  end

  def email; end
end
