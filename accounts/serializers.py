from decimal import Clamped
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from sales.models import SalesCash
from .models.bank_account_model import Bank, Transition
User = get_user_model()




class BankAccountSerializer(serializers.ModelSerializer):
     class Meta:
          model = Bank
          fields = "__all__"
          
     
     def create(self, validated_data):
          bank =  Bank.objects.create( 
                                        company_id=self.context['request'].user.company_id,
                                        creator= self.context['request'].user,
                                        company= self.context['request'].user.company,
                                        **validated_data
                                        )
          return bank
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)


class TransitionSerializer(serializers.ModelSerializer):
     # bank_account = BankAccountSerializer(required=False, read_only=True)
     class Meta:
          model = Transition
          fields = "__all__"
          
     
     def create(self, validated_data):
          # transition_data = validated_data.pop('amount')
          transferFund =  Transition.objects.create( 
                                        company_id=self.context['request'].user.company_id,
                                        creator= self.context['request'].user,
                                        company= self.context['request'].user.company,
                                        **validated_data
                                        )
          if transferFund.type_of_transfer == "Deposit":
               salesCash = SalesCash.objects.get(company_id=transferFund.company_id )
               bank = Bank.objects.get(id=transferFund.bank_account.id)
               
               transferFund.bank_balance = bank.current_balance
               transferFund.cash_balance =  salesCash.amount
               transferFund.account_number = bank.bank_account_number
               transferFund.save()
               # print("Deposit")
               # print(salesCash.amount)
               # print(transferFund.amount)
               bank.current_balance = bank.current_balance + transferFund.amount
               bank.save()
               salesCash.amount = salesCash.amount - transferFund.amount
               salesCash.save()
          elif transferFund.type_of_transfer == "Withdraw":
               salesCash = SalesCash.objects.get(company_id=transferFund.company_id )
               bank = Bank.objects.get(id=transferFund.bank_account.id)
               # print("Withdraw")
               # print(salesCash.amount)
               # print(transferFund.amount)
               transferFund.bank_balance = bank.current_balance
               transferFund.cash_balance =  salesCash.amount
               transferFund.account_number = bank.bank_account_number
               transferFund.save()
               
               bank.current_balance = bank.current_balance - transferFund.amount
               bank.save()
               salesCash.amount = salesCash.amount + transferFund.amount
               salesCash.save()
               
          else:
               pass
          return transferFund
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)


class GetTransitionSerializer(serializers.ModelSerializer):
     bank_account = BankAccountSerializer(required=False)
     class Meta:
          model = Transition
          fields = "__all__"


