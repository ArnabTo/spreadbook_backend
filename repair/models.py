from django.utils.timezone import now
from django.db.models.signals import pre_save,post_save
from django.dispatch import receiver
from customers.models import Customer
from sales.models import SalesCash
from django.db import models
from sales.models import Sale
from products.models import Product
from suppliers.models import Supplier
import uuid
from django.contrib.auth import get_user_model
User = get_user_model()


STATUS_CHOICE = (
     ('paid', 'paid'),
     ('pending', 'pending'),
     ('overdue', 'overdue'),
     )

PAYMENT_CHOICE = (
     ('hand cash', 'hand cash'),
     ('cash on delivery', 'cash on delivery'),
     ('bKash', 'bKash'),
     ('উপায় (upay)', 'উপায় (upay)'),
     ('nagad', 'nagad'),
     ('dutch-bangla bank', 'dutch-bangla bank'),
     ('bank payment', 'bank payment'),
     )



class WarrentyProductList(models.Model):
     id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     creator     = models.ForeignKey(User,on_delete=models.SET_NULL,related_name='owner_repair', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)
     
     invoiceNumber = models.CharField(max_length=100, null=True, blank=True)
     customer = models.ForeignKey(Customer, related_name="warrenty", on_delete=models.SET_NULL,  null=True, blank=True)

     code = models.CharField(max_length=20, null=True, blank=True)
     serial = models.CharField(max_length=20, null=True, blank=True)
     
     price = models.FloatField(default=0, blank=True, null=True)
     repair_count = models.IntegerField(default=0 ,null=True, blank=True)
     service_name = models.CharField(max_length=500, default="" ,blank=True, null=True)
     description= models.TextField(max_length=500, default="" ,blank=True, null=True)

     warrenty_period = models.DateTimeField(blank=True, null=True)

     createDate = models.DateTimeField(default=now, blank=True, null=True)
     updatedAt = models.DateTimeField(auto_now=True)
     

class RepairCash(models.Model):
     """ Sale model for storing sale data🛢 """
     id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     creator     = models.ForeignKey(User,on_delete=models.CASCADE,related_name='owner_reapir_cash', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)
     
     amount = models.FloatField(default=0, blank=True, null=True)
     due = models.FloatField(default=0, blank=True, null=True)

     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
     
     
class RepairHistory(models.Model):
     """ Sale model for storing sale data🛢 """
     id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     creator     = models.ForeignKey(User,on_delete=models.CASCADE,related_name='owner_repair_cash_history', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)
     
     reference_id = models.CharField(max_length=100, null=True, blank=True)
     reference_name = models.CharField(max_length=100, null=True, blank=True)
     
     # Last amount befor record creation 
     cash_balance = models.FloatField(verbose_name='Last Cash Balance', null=True, blank=True)

     paid = models.FloatField(default=0, blank=True, null=True)
     total = models.FloatField(default=0, blank=True, null=True)
     due = models.FloatField(default=0, blank=True, null=True)

     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
     
     
     
class Repair(models.Model):
     """ Sale model for storing sale data🛢 """
     id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     creator     = models.ForeignKey(User,on_delete=models.CASCADE,related_name='owner_repair_service', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)

     # new_id = models.AutoField(unique=True, editable=False, primary_key=False)
     invoiceNumber = models.CharField(max_length=100, null=True, blank=True)
     
     # creator = models.ForeignKey(Customer, on_delete=models.CASCADE,  null=True, blank=True)
     # product = models.ForeignKey(Product, on_delete=models.CASCADE)
     status = models.CharField(max_length=100, choices=STATUS_CHOICE, default="draft", blank=True, null=True)
     
     invoiceFrom = models.ForeignKey(User, related_name="repairFrom", on_delete=models.SET_NULL,  null=True, blank=True)
     invoiceTo = models.ForeignKey(Customer, related_name="repairTo", on_delete=models.SET_NULL,  null=True, blank=True)
     
     # TODO: Future implementation of sale model.

     # invoice_date = models.DateTimeField()
     # invoice_time = models.DateTimeField()
     # invoice_due_date = models.DateField()
     # invoice_due_time= models.DateTimeField()
     
     
     payment_method = models.CharField(max_length=100, choices=PAYMENT_CHOICE, default="hand cash", blank=True, null=True)
     is_paid = models.BooleanField(
          verbose_name='Is Paid',
          help_text='Is the service paid? If yes, the status will be set to paid.',
          default=False,
     )
     
     taxes = models.FloatField(default=0, blank=True, null=True)
     taxes_value = models.FloatField( default=0, blank=True, null=True)
     discount = models.FloatField(default=0, blank=True, null=True)
     totalQty = models.FloatField(default=0, blank=True, null=True)
     totalAmount = models.FloatField(default=0, blank=True, null=True)
     subTotal = models.FloatField(default=0, blank=True, null=True)
     advance = models.FloatField(default=0, blank=True, null=True)
     due = models.FloatField(default=0, blank=True, null=True)
     
     cashAmount = models.FloatField(default=0, blank=True, null=True)
     change = models.FloatField(default=0, blank=True, null=True)
     
     commission = models.FloatField(default=0, blank=True, null=True)
     
     shipping = models.FloatField(default=0, blank=True, null=True)
     total = models.FloatField(default=0, blank=True, null=True)
     total_profit  = models.FloatField(default=0, blank=True, null=True)
     
     dueDate   = models.DateTimeField(blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
     
     # def get_timestamp(self):
     #      epoch = datetime.utcfromtimestamp(0)
     #      delta = self.createDate - epoch
     #      return int(delta.total_seconds())




class EnquiryItems(models.Model):
	repair_invoice = models.ForeignKey(Repair,related_name='items', on_delete=models.CASCADE, blank=True, null=True)
     
	PROBLEM_CATEGORY_CHOICES = (
		('Hardware','Hardware'),
		('Software','Software'),
	)

	CONDITION_CHOICE =(
		('Repair','Repair'),
  		('Replace','Replace'),
	)

	STATUS_CHOICES = (
		('Enquired','Enquired'),
		('Checked','Checked'),		# This is amazing
		('Repaired','Repaired'),		# Changed from Update Form when Components are added and Repair Charge is added
		('Completed','Completed'),		# Changed to when Final Receipt is Generated
		('Rejected','Rejected'),
	)

	enquiryDate = models.DateField(blank=True, null=True)

	# customerName = models.CharField(max_length = 80, blank=True, null=True)
	# contactNo = models.CharField(max_length = 50, blank=True, null=True)
	# email = models.CharField(max_length = 50, blank=True, null=True)
	# address = models.TextField(blank=True, null=True)
	conditionChoice = models.CharField(max_length = 30, choices = CONDITION_CHOICE, blank=True, null=True)
	deviceType = models.CharField(max_length = 50, blank=True, null=True)
	brand = models.CharField(max_length = 50, blank=True, null=True)
	deviceModel = models.CharField(max_length = 50, blank=True, null=True)
	code = models.CharField(max_length=20, null=True, blank=True)
	serial = models.CharField(max_length = 50, blank=True, null=True)

	problemCategory = models.CharField(max_length = 30, choices = PROBLEM_CATEGORY_CHOICES, blank=True, null=True)
	problem = models.CharField(max_length = 100, blank=True, null=True)
	description = models.TextField(blank=True, null=True)

	deviceCondition = models.TextField(blank=True, null=True)

	quantity = models.FloatField(default=0)
	price = models.FloatField(default=0)
	advance = models.FloatField(default=0)
	total = models.FloatField(default=0)

	status = models.CharField(max_length=30, choices = STATUS_CHOICES, default='Enquired')

	updateAt = models.DateTimeField(auto_now=True)
	createDate = models.DateTimeField(default=now, blank=True, null=True)
	# def __str__(self):
	# 	return str(self.id) + " : "  + self.status + " : "  + self.customerName + " : " + self.brand + " " + self.deviceModel


class TestDetail(models.Model):
	Enquiry = models.ForeignKey(EnquiryItems, on_delete=models.CASCADE)
	actualProblem = models.CharField(max_length = 50)
	actualProblemDescription = models.TextField(blank=True)

	# def __str__(self):
	# 	return str(self.Enquiry.id) + " : " + str(self.Enquiry.status) + " : " + self.Enquiry.customerName + " : " + self.actualProblem

class RepairDetail(models.Model):
	Enquiry = models.ForeignKey(EnquiryItems, on_delete=models.CASCADE)
	componentsUsed = models.TextField(blank=True)
	repairCharge = models.IntegerField(blank=True)
	otherCharge = models.IntegerField(blank=True)
	totalPrice = models.IntegerField(blank=True)

	# def __str__(self):
	# 	return str(self.Enquiry.id) + " : " + str(self.Enquiry.status) + " : " + self.Enquiry.customerName + " : " + str(self.totalPrice)

class TrialPeriod(models.Model):
	ID = models.AutoField(primary_key=True)
	counter = models.IntegerField()
	date = models.DateField()