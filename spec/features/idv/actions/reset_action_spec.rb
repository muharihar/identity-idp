require 'rails_helper'

feature 'doc auth reset action' do
  include IdvStepHelper
  include DocAuthHelper

  before do
    enable_doc_auth
    complete_doc_auth_steps_before_front_image_step
  end

  it 'resets doc auth to the first step' do
    expect(page).to have_current_path(idv_doc_auth_front_image_step)

    click_on t('doc_auth.buttons.start_over')

    expect(page).to have_current_path(idv_doc_auth_ssn_step)
  end
end
