from django.db.models.aggregates import Count
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin,UpdateModelMixin,RetrieveModelMixin,DestroyModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated,AllowAny
from store.pagination import DefaultPagination
from .models import Cart, CartItem, Collection, Customer, Order, Product, Review
from .serializers import AddCartItemSerializer, CartItemSerializer, CartSerializer, CollectionSerializer, CreateOrderSerializer, CustomerSerializer, OrderSerializer, ProductSerializer, ReviewSerializer, UpdateCartItemSerializer, UpdateOrderSerializer

class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = DefaultPagination
    def get_serializer_context(self):
        return {'request': self.request}

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if product.orderitems.count() > 0:
            return Response({'error': 'Product cannot be deleted because it is associated with an order item.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CollectionViewSet(ModelViewSet):
    queryset = Collection.objects.annotate(
        products_count=Count('products')).all()
    serializer_class = CollectionSerializer

    def delete(self, request, pk):
        collection = get_object_or_404(Collection, pk=pk)
        if collection.products.count() > 0:
            return Response({'error': 'Collection cannot be deleted because it includes one or more products.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(product_id=self.kwargs['product_pk'])

    def get_serializer_context(self):
        return {'product_id': self.kwargs['product_pk']}

class CartViewSet(CreateModelMixin,RetrieveModelMixin,DestroyModelMixin,GenericViewSet):
    queryset = Cart.objects.prefetch_related('items__product').all()
    serializer_class = CartSerializer

class CartItemViewSet(ModelViewSet):
    http_method_names=['get','post','delete','patch']
    def get_queryset(self):
        return CartItem.objects.filter(cart_id=self.kwargs['cart_pk'])\
        .select_related('product')
    def get_serializer_context(self):
        return {'cart_id':self.kwargs['cart_pk']}
    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        if self.request.method == "PATCH":
            return UpdateCartItemSerializer
        return CartItemSerializer
    
class CustomerViewSet(CreateModelMixin,RetrieveModelMixin,UpdateModelMixin,GenericViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['GET','PUT'])
    def me(self, request):
        customer = Customer.objects.get(user_id=request.user.id)
        if request.method == "GET":
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        elif request.method == "PUT":
            serializer = CustomerSerializer(customer,request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

class OrderViewSet(ModelViewSet):
    http_method_names=["post","get","patch","delete"]
    permission_classes = [IsAuthenticated]
    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(data=request.data,context={'user_id': self.request.user.id})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def get_queryset(self):
        return Order.objects.filter(customer_id = self.request.user.id)
    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateOrderSerializer
        elif self.request.method == "PATCH":
            return UpdateOrderSerializer
        return OrderSerializer