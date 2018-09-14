module Flow
  class BaseFlow
    attr_accessor :flow_session
    attr_reader :steps, :actions, :current_user, :params

    def initialize(steps, actions, session, current_user)
      @current_user = current_user
      @steps = steps.with_indifferent_access
      @actions = actions.with_indifferent_access
      @params = nil
      @flow_session = session
    end

    def next_step
      step, _klass = steps.detect do |_step, klass|
        !@flow_session[klass.to_s]
      end
      step
    end

    def handle(step, params)
      @flow_session[:error_message] = nil
      handler = steps[step] || actions[step]
      return failure("Unhandled step #{step}") unless handler
      @params = params
      wrap_send(handler)
    end

    private

    def wrap_send(handler)
      obj = handler.new(self)
      value = obj.base_call
      form_response(obj, value)
    end

    def form_response(obj, value)
      response = value.class == FormResponse ? value : FormResponse.new(success: true, errors: {})
      obj.mark_step_complete if response.success?
      response
    end
  end
end
