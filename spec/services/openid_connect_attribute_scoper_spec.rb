require 'rails_helper'

RSpec.describe OpenidConnectAttributeScoper do
  subject(:scoper) { OpenidConnectAttributeScoper.new(scope) }

  describe '#scopes' do
    subject(:scopes) { scoper.scopes }

    context 'with a string of space-separate scopes' do
      let(:scope) { 'openid email profile' }

      it 'parses scopes' do
        expect(scopes).to eq(%w(openid email profile))
      end
    end

    context 'with an array' do
      let(:scope) { %w(fakescope openid email profile) }

      it 'filters the array' do
        expect(scopes).to eq(%w(openid email profile))
      end
    end
  end

  describe '#filter' do
    subject(:filtered) { scoper.filter(user_info) }

    let(:scope) { 'openid' }
    let(:user_info) do
      {
        sub: 'abcdef',
        iss: 'https://login.gov',
        email: 'foo@example.com',
        email_verified: true,
        given_name: 'John',
        family_name: 'Jones',
        birthdate: '1970-01-01',
        phone: '+1 (555) 555-5555',
        phone_verified: true,
        address: {
          formatted: "123 Fake St\nWashington, DC 12345",
          street_address: '123 Fake St',
          locality: 'Washington',
          region: 'DC',
          postal_code: '12345',
        },
        social_security_number: '666661234',
      }
    end

    context 'minimum scope' do
      let(:scope) { 'openid' }

      it 'is only sub and iss' do
        expect(filtered).to eq(
          sub: 'abcdef',
          iss: 'https://login.gov'
        )
      end
    end

    context 'with address scope' do
      let(:scope) { 'openid address' }

      it 'includes the address attribute' do
        expect(filtered[:address]).to be_present
      end
    end

    context 'with email scope' do
      let(:scope) { 'openid email' }

      it 'includes the email and email_verified attributes' do
        expect(filtered[:email]).to be_present
        expect(filtered[:email_verified]).to eq(true)
      end
    end

    context 'with phone scope' do
      let(:scope) { 'openid phone' }

      it 'includes the phone and email_verified attributes' do
        expect(filtered[:phone]).to be_present
        expect(filtered[:phone_verified]).to eq(true)
      end
    end

    context 'with profile scope' do
      let(:scope) { 'openid profile' }

      it 'includes name attributes and birthdate' do
        expect(filtered[:given_name]).to be_present
        expect(filtered[:family_name]).to be_present
        expect(filtered[:birthdate]).to be_present
      end
    end

    context 'with social_security_number scope' do
      let(:scope) { 'openid social_security_number' }

      it 'includes social_security_number' do
        expect(filtered[:social_security_number]).to be_present
      end
    end
  end

  describe '#requested_attributes' do
    let(:scope) { 'email profile' }
    subject(:requested_attributes) { scoper.requested_attributes }

    it 'is the array of attributes corresponding to the scopes' do
      expect(requested_attributes).to eq(%w(email given_name family_name birthdate))
    end
  end
end