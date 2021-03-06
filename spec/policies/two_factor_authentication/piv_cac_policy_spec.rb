require 'rails_helper'

describe TwoFactorAuthentication::PivCacPolicy do
  let(:subject) { described_class.new(user) }

  describe '#available?' do
    context 'when a user has no identities' do
      let(:user) { create(:user) }

      it 'does not allow piv/cac' do
        expect(subject.available?).to be_falsey
      end
    end

    context 'when a user has an identity' do
      let(:user) { create(:user) }

      let(:service_provider) do
        create(:service_provider)
      end

      let(:identity_with_sp) do
        Identity.create(
          user_id: user.id,
          service_provider: service_provider.issuer
        )
      end

      before(:each) do
        user.identities << [identity_with_sp]
      end

      context 'not allowing it' do
        it 'does not allow piv/cac' do
          expect(subject.available?).to be_falsey
        end
      end

      context 'allowing it' do
        before(:each) do
          allow(Figaro.env).to receive(:piv_cac_agencies).and_return(
            [service_provider.agency].to_json
          )
          PivCacService.send(:reset_piv_cac_avaialable_agencies)
        end

        it 'does allows piv/cac' do
          expect(subject.available?).to be_truthy
        end
      end
    end

    context 'when a user has a piv/cac associated' do
      let(:user) { create(:user, :with_piv_or_cac) }

      it 'disallows piv/cac setup' do
        expect(subject.available?).to be_falsey
      end

      it 'allow piv/cac visibility' do
        expect(subject.visible?).to be_truthy
      end
    end
  end

  describe '#configured?' do
    context 'without a piv configured' do
      let(:user) { build(:user) }

      it { expect(subject.configured?).to be_falsey }
    end

    context 'with a piv configured' do
      let(:user) { build(:user, :with_piv_or_cac) }

      it { expect(subject.configured?).to be_truthy }
    end
  end

  describe '#enabled?' do
    context 'without a piv configured' do
      let(:user) { build(:user) }

      it { expect(subject.configured?).to be_falsey }
    end

    context 'with a piv configured' do
      let(:user) { build(:user, :with_piv_or_cac) }

      it { expect(subject.configured?).to be_truthy }
    end
  end

  describe '#visible?' do
    let(:user) { build(:user) }

    context 'when enabled' do
      before(:each) do
        allow(subject).to receive(:enabled?).and_return(true)
      end

      it { expect(subject.visible?).to be_truthy }
    end

    context 'when associated with a supported identity' do
      before(:each) do
        identity = double
        allow(identity).to receive(:piv_cac_available?).and_return(true)
        allow(user).to receive(:identities).and_return([identity])
      end

      it { expect(subject.visible?).to be_truthy }
    end

    context 'when not enabled and not a supported identity' do
      before(:each) do
        identity = double
        allow(identity).to receive(:piv_cac_available?).and_return(false)
        allow(user).to receive(:identities).and_return([identity])
        allow(subject).to receive(:enabled?).and_return(false)
      end

      it { expect(subject.visible?).to be_falsey }
    end
  end
end
