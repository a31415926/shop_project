from django.db import models
from accounts.models import CustomUser
from django.db.models.signals import post_delete
from django.urls import reverse
from datetime import date
import os


class PriceMatrix(models.Model):
    name = models.CharField(max_length=200, default='Name matrix', verbose_name='Название')


class PriceMatrixItem(models.Model):
    type_item_choices = [
        ('relative', 'В процентах'),
        ('fixed', 'Фиксированная'),    
    ]
    min_value = models.FloatField(default=0, verbose_name='От') 
    max_value = models.FloatField(default=0, verbose_name='До')
    type_item = models.CharField(max_length=50, choices=type_item_choices, default='fixed', verbose_name='Тип')
    value = models.FloatField(default=0, verbose_name='Значение')
    matrix = models.ForeignKey(PriceMatrix, on_delete=models.CASCADE)


class Product(models.Model):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    type_product = models.CharField(choices=[('material', 'Материальный'),('file', 'Файл'),],
        default='material', max_length=100, verbose_name='Тип товара')
    file_digit = models.FileField(default=None, blank=True, null=True, verbose_name='Файл (при тип товара - Файл)')
    title = models.CharField(max_length=300, default='Noname')
    stock = models.IntegerField(blank=True, default=0, null=True)
    brand = models.CharField(blank=True, null=True, max_length=150)
    desc = models.TextField(blank=True, null=True, default='')
    vendor_code = models.CharField(max_length=100, blank=True, null=True)
    price = models.FloatField(default=0, blank=True, null=True)
    old_price = models.FloatField(default=0, blank=True, null=True)
    cid = models.ManyToManyField('Categories', related_name = 'category')
    date_add = models.DateTimeField(auto_now_add=True)
    date_edit = models.DateTimeField(auto_now=True)
    photo = models.FileField(default=None, null=True, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.price = round(self.price, 2)
        self.old_price = round(self.old_price, 2)
        super(Product, self).save(*args, **kwargs)
    
    def delete(self):
        self.photo.delete()
        super(Product, self).delete()


class Categories(models.Model):
    name = models.CharField(max_length=250, default='Noname cat', unique=True)
    parent_id = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    state = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Currency(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=15, blank=True)
    rate = models.FloatField(default=1)
    disp = models.CharField(max_length=20, blank=True, null=True, default='y.e.')

    def __str__(self):
        return self.name



class Delivery(models.Model):
    name = models.CharField(max_length=350, default='Delivery')
    description = models.TextField(blank=True, null=True)
    matrix = models.ForeignKey(PriceMatrix, blank=True, null=True, default=None, on_delete=models.PROTECT)

    def __str__(self):
        return self.name


    @classmethod
    def calc_cost_of_delivery(cls, id_delivery, total_amount):
        delivery = cls.objects.get(pk=id_delivery)
        delivery_matrix = delivery.matrix
        if not delivery_matrix:
            return 0
        items = delivery_matrix.pricematrixitem_set.all()
        cost_of_delivery = 0
        for item in items:
            if item.min_value <= total_amount < item.max_value:
                if item.type_item =='fixed':
                    cost_of_delivery = item.value
                    break
                elif item.type_item == 'relative':
                    cost_of_delivery = total_amount /100 * item.value
                    break

        cost_of_delivery = round(cost_of_delivery, 2)
        return cost_of_delivery

class Promocode(models.Model):
    #table with promocode
    type_discount_choices = [
        ('fixed', 'Фиксированная'),
        ('relative', 'Относительная'),
    ]
    type_promo_choices = [
        ('onceuse', 'Одноразовые'),
        ('reusable', 'Многоразовые'),
    ]
    code = models.CharField(max_length=200, unique=True)
    type_code = models.CharField(default='fixed', choices=type_discount_choices, max_length=50)
    amount_of_discount = models.FloatField(default=0)
    type_promo = models.CharField(default='reusable', choices=type_promo_choices, max_length=50)
    status = models.BooleanField(default=True)
    start_promo = models.DateField(blank=True, null = True)
    end_promo = models.DateField(blank=True, null = True)

    def __str__(self):
        return self.code

    @classmethod
    def is_promo(cls, promocode):
        is_promo = cls.objects.filter(code = promocode, status = True)[0]
        if is_promo:
            if is_promo.start_promo:
                if is_promo.end_promo:
                    if is_promo.start_promo <= date.today() <= is_promo.end_promo:
                        return True
                else:
                    if is_promo.start_promo <= date.today():
                        return True
            elif is_promo.end_promo:
                if date.today() <= is_promo.end_promo:
                    return True
            else:
                return True
            return False
        return False
    

    @classmethod
    def get_discount(cls, total_sum, promocode):
        promo = cls.objects.get(code=promocode)
        if promo.type_code == 'fixed':
                discount = promo.amount_of_discount
        elif promo.type_code == 'relative':
            discount = total_sum * promo.amount_of_discount / 100
        return discount
    
    def get_sum_discount(self, total_amount):
        if self.type_code == 'fixed':
                discount = self.amount_of_discount
        elif self.type_code == 'relative':
            discount = total_amount * self.amount_of_discount / 100
        return discount


class Order(models.Model):
    #user = 
    status_choices = [
        ('new', 'Новый'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('finished', 'Завершен'),
        ('cancel', 'Отменен'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True)
    full_amount = models.FloatField(default=0, verbose_name='Полная стоимость товаров в у.е.')
    total_amount = models.FloatField(default=0, verbose_name='Сумма к оплате в у.е.')
    date_create = models.DateTimeField(auto_now_add=True)
    status = models.CharField(default='new', choices=status_choices, max_length=50, verbose_name='Статус заказа')
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name='Валюта')
    rate_currency = models.FloatField(default=1, verbose_name='Курс валюты в момент заказа')
    promo = models.ForeignKey(Promocode, on_delete=models.PROTECT, blank=True, null=True, default='', verbose_name='Промокод')
    delivery_method = models.ForeignKey(Delivery, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Способ доставки')
    cost_of_delivery = models.FloatField(default=0, verbose_name='Стоимость доставки')


    class Meta:
        permissions = (('change_status','Can change status order'),)


    def get_absolute_url(self):
        return reverse('invoice_page', args=[self.id])


    def save(self, *args, **kwargs):
        self.full_amount = round(self.full_amount, 2)
        self.total_amount = round(self.total_amount, 2)
        self.cost_of_delivery = round(self.cost_of_delivery, 2)
        self.rate_currency = round(self.rate_currency, 2)
        super(Order, self).save(*args, **kwargs)


    @classmethod
    def change_status(cls, id_order, new_status):
        obj = cls.objects.get(pk = id_order)
        obj.status = new_status
        obj.save()

    def recalc_order(self):
        order_item = self.orderitem_set.all()
        self.full_amount = order_item.get_total_amount()
        self.get_sum_discount = self.promo.get_sum_discount(self.full_amount)
        self.cost_of_delivery = Delivery.calc_cost_of_delivery(self.delivery_method.id, self.full_amount + self.get_sum_discount)
        self.total_amount = self.full_amount + self.get_sum_discount + self.cost_of_delivery
        self.cost_of_delivery_on_curr = self.cost_of_delivery * self.rate_currency
        self.total_amount_on_curr = self.total_amount * self.rate_currency
        self.full_amount_on_curr = self.full_amount * self.rate_currency
        self.save()


class OrdetItemQuerySet(models.QuerySet):

    def get_total_amount(self):
        total = 0
        for i in self:
            total += i.qty * i.cost
        return total

class OrderItemManager(models.Manager):
    _queryset_class = OrdetItemQuerySet


class OrderItem(models.Model):
    #содержимое заказов
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    id_good = models.IntegerField(default=1)
    title_good = models.CharField(default='Noname', max_length=300)
    cost = models.FloatField(default=1)
    qty = models.IntegerField(default=1)
    order = models.ForeignKey('Order', on_delete=models.CASCADE)


    objects = OrderItemManager()


    @classmethod
    def add_item(cls, data):
        if data.get('pk'):
            try:
                obj = cls.objects.get(pk = data.get('pk'))
                price = data.get('price')/obj.order.rate_currency if data.get('price') else obj.cost 
                obj.cost = price
                obj.qty = data.get('qty', obj.qty)
                obj.save()
            except cls.DoesNotExist:
                return False
        else:
            item, create = cls.objects.update_or_create(
                order = data.get('order'),
                product = data.get('product'),
                defaults = {
                    'title_good':data.get('title', data['product'].title),
                    'qty':data.get('qty', 1),
                    'cost':data.get('price', data['product'].price)
                }
            )
            if not create:
                item.qty += 1
                item.save()
        




class FileTelegram(models.Model):

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    id_file = models.CharField(max_length=100)


class BasketQuerySet(models.QuerySet):

    def get_total_amount(self):
        total = 0
        for i in self:
            total += i.qty * i.price
        return total

class BasketManager(models.Manager):
    _queryset_class = BasketQuerySet


class BasketItem(models.Model):

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар', null=True)
    qty = models.IntegerField(default=1, verbose_name='Количество')
    price = models.FloatField(verbose_name='Стоимость за ед.')
    date_add = models.DateTimeField(auto_now=True)

    objects = BasketManager()

    class Meta:
        
        permissions = (
            ('show_all_baskets', 'Просматривать корзины других пользователей'),
        )        
