module Idv
  module Utils
    class PiiFromDoc
      VALUE = {
        'First Name' => :first_name,
        'Middle Name' => :middle_name,
        'Surname' => :last_name,
        'Address Line 1' => :address1,
        'Address City' => :city,
        'Address State' => :state,
        'Address Postal Code' => :zipcode,
        'Birth Date' => :dob,
      }.freeze

      def initialize(id_data_fields)
        @name_to_value = {}
        id_data_fields['Fields'].each do |field|
          @name_to_value[field['Name']] = field['Value']
        end
      end

      def call(ssn, phone)
        VALUE.each do |key, value|
          hash[value] = @name_to_value[key]
        end
        hash[:dob] = convert_date(hash[:dob])
        hash[:ssn] = ssn
        hash[:phone] = phone
        hash
      end

      private

      def hash
        @hash ||= {}
      end

      def convert_date(date)
        Date.strptime((date[6..-3].to_f / 1000).to_s, '%s').strftime('%m/%d/%Y')
      end
    end
  end
end
