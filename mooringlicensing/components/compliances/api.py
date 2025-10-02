import logging

from rest_framework_datatables.filters import DatatablesFilterBackend
from django.db.models import Q, CharField, Value
from django.db.models.functions import Concat
from django.db import transaction
from django.conf import settings
from rest_framework import viewsets, serializers, views, mixins
from rest_framework.decorators import action as detail_route
from rest_framework.response import Response
from django.core.cache import cache
from ledger_api_client.ledger_models import EmailUserRO as EmailUser
from mooringlicensing.components.main.decorators import basic_exception_handler
from ledger_api_client.managed_models import SystemUser

from mooringlicensing.components.compliances.models import (
   Compliance,
   ComplianceAmendmentRequest,
   ComplianceAmendmentReason
)
from mooringlicensing.components.compliances.serializers import (
    ComplianceSerializer,
    InternalComplianceSerializer,
    SaveComplianceSerializer,
    ComplianceActionSerializer,
    ComplianceCommsSerializer,
    ComplianceAmendmentRequestSerializer,
    CompAmendmentRequestDisplaySerializer, ListComplianceSerializer
)
from mooringlicensing.components.proposals.models import ProposalApplicant
from mooringlicensing.helpers import is_customer, is_internal
from rest_framework_datatables.pagination import DatatablesPageNumberPagination

from rest_framework.permissions import IsAuthenticated
from mooringlicensing.components.compliances.permissions import (
    InternalCompliancePermission,
    ComplianceAssessorPermission
)

logger = logging.getLogger(__name__)

class ComplianceViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    serializer_class = ComplianceSerializer
    queryset = Compliance.objects.none()
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        if is_internal(self.request):
            return Compliance.objects.all()
        elif is_customer(self.request):
            queryset =  Compliance.objects.filter(
                Q(proposal__proposal_applicant__email_user_id=self.request.user.id)
            ).exclude(processing_status='discarded')
            return queryset
        return Compliance.objects.none()

    @detail_route(methods=['GET',], detail=True, permission_classes=[InternalCompliancePermission])
    def internal_compliance(self, request, *args, **kwargs):
        if is_internal(request):
            instance = self.get_object()
            serializer = InternalComplianceSerializer(instance,context={'request':request})
            return Response(serializer.data)
        return Response()

    @detail_route(methods=['POST',], detail=True)
    @basic_exception_handler
    def submit(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = self.get_object()

            # Can only modify if Due or Future.
            if instance.processing_status not in ['due', 'future','overdue']:
                raise serializers.ValidationError('The status of this application means it cannot be modified: {}'
                                                    .format(instance.processing_status))

            if instance.proposal.applicant_email != request.user.email and not is_internal(request): 
                raise serializers.ValidationError('You are not authorised to modify this application.')

            data = {
                'text': request.data.get('detail'),
            }

            serializer = SaveComplianceSerializer(instance, data=data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            instance.submit(request)

            serializer = self.get_serializer(instance)
            return Response(serializer.data)

    @detail_route(methods=['GET',], detail=True, permission_classes=[ComplianceAssessorPermission])
    @basic_exception_handler
    def assign_request_user(self, request, *args, **kwargs):
        if is_internal(request):
            instance = self.get_object()
            instance.assign_to(request.user,request)
            serializer = InternalComplianceSerializer(instance, context={'request': request})
            return Response(serializer.data)
        return Response()

    @detail_route(methods=['POST',], detail=True)
    @basic_exception_handler
    def delete_document(self, request, *args, **kwargs):
        if (
            is_internal(request) or 
            (
                self.processing_status in ['future','due','overdue'] and
                (request.user.id == self.holder_id or is_internal(request))
            )
        ):
            instance = self.get_object()
            doc=request.data.get('document')
            instance.delete_document(request, doc)
            serializer = ComplianceSerializer(instance)
            return Response(serializer.data)
        else:
            raise serializers.ValidationError("User not authorised to delete document")

    @detail_route(methods=['POST',], detail=True, permission_classes=[ComplianceAssessorPermission])
    @basic_exception_handler
    def assign_to(self, request, *args, **kwargs):
        if (is_internal(request)):
            instance = self.get_object()
            user_id = request.data.get('user_id',None)
            user = None
            if not user_id:
                raise serializers.ValiationError('A user id is required')
            try:
                user = EmailUser.objects.get(id=user_id)
            except EmailUser.DoesNotExist:
                raise serializers.ValidationError('A user with the id passed in does not exist')
            instance.assign_to(user,request)
            serializer = InternalComplianceSerializer(instance, context={'request': request})
            return Response(serializer.data)
        raise serializers.ValidationError("User not authorised to assign compliance")

    @detail_route(methods=['GET',], detail=True, permission_classes=[ComplianceAssessorPermission])
    @basic_exception_handler
    def unassign(self, request, *args, **kwargs):
        if (is_internal(request)):
            instance = self.get_object()
            instance.unassign(request)
            serializer = InternalComplianceSerializer(instance, context={'request': request})
            return Response(serializer.data)
        raise serializers.ValidationError("User not authorised to unassign compliance")

    @detail_route(methods=['GET',], detail=True, permission_classes=[ComplianceAssessorPermission])
    @basic_exception_handler
    def accept(self, request, *args, **kwargs):
        if (is_internal(request)):
            instance = self.get_object()
            instance.accept(request)
            serializer = InternalComplianceSerializer(instance, context={'request': request})
            return Response(serializer.data)
        raise serializers.ValidationError("User not authorised to accept compliance")
    
    @detail_route(methods=['GET',], detail=True, permission_classes=[ComplianceAssessorPermission])
    def discard(self, request, *args, **kwargs):
        if (is_internal(request)):
            instance = self.get_object()
            if instance.processing_status == Compliance.PROCESSING_STATUS_WITH_ASSESSOR and request.user in instance.allowed_assessors:
                instance.processing_status = Compliance.PROCESSING_STATUS_DISCARDED
                instance.save()
                serializer = InternalComplianceSerializer(instance, context={'request': request})
                instance.log_user_action(f"Compliance {instance} discarded.", request)
                return Response(serializer.data)
        raise serializers.ValidationError("User not authorised to discard compliance")
    
    @detail_route(methods=['GET',], detail=True)
    @basic_exception_handler
    def amendment_request(self, request, *args, **kwargs):
        instance = self.get_object()
        qs = instance.amendment_requests
        qs = qs.filter(status = 'requested')
        serializer = CompAmendmentRequestDisplaySerializer(qs,many=True)
        instance.log_user_action(f"Amendment requested for Compliance {instance}.", request)
        return Response(serializer.data)

    @detail_route(methods=['GET',], detail=True, permission_classes=[InternalCompliancePermission])
    @basic_exception_handler
    def action_log(self, request, *args, **kwargs):
        if (is_internal(request)):
            instance = self.get_object()
            qs = instance.action_logs.all()
            serializer = ComplianceActionSerializer(qs,many=True)
            return Response(serializer.data)
        return Response()

    @detail_route(methods=['GET',], detail=True, permission_classes=[InternalCompliancePermission])
    @basic_exception_handler
    def comms_log(self, request, *args, **kwargs):
        if (is_internal(request)):
            instance = self.get_object()
            qs = instance.comms_logs.all()
            serializer = ComplianceCommsSerializer(qs,many=True)
            return Response(serializer.data)
        return Response()

    @detail_route(methods=['POST',], detail=True, permission_classes=[InternalCompliancePermission])
    @basic_exception_handler
    def add_comms_log(self, request, *args, **kwargs):
        if (is_internal(request)):
            with transaction.atomic():
                instance = self.get_object()
                mutable=request.data._mutable
                request.data._mutable=True
                request.data['compliance'] = u'{}'.format(instance.id)
                request.data['staff'] = u'{}'.format(request.user.id)
                request.data._mutable=mutable
                serializer = ComplianceCommsSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                comms = serializer.save()
                # Save the files
                for f in request.FILES:
                    document = comms.documents.create(
                        name = str(request.FILES[f]),
                        _file = request.FILES[f]
                    )
                # End Save Documents

                instance.log_user_action(f'User added comms log.', request)

                return Response(serializer.data)
        raise serializers.ValidationError("User not authorised to add comms log")
    

class ComplianceAmendmentRequestViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    queryset = ComplianceAmendmentRequest.objects.all()
    serializer_class = ComplianceAmendmentRequestSerializer
    permission_classes=[ComplianceAssessorPermission]

    def get_queryset(self):
        queryset = ComplianceAmendmentRequest.objects.none()
        if is_internal(self.request):
            queryset = ComplianceAmendmentRequest.objects.all()
        return queryset

    @basic_exception_handler
    def create(self, request, *args, **kwargs):
        if is_internal(request):
            serializer = self.get_serializer(data= request.data)
            serializer.is_valid(raise_exception = True)
            instance = serializer.save()
            instance.generate_amendment(request)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        else:
            raise serializers.ValidationError("user not authorised to make an amendment request")


class ComplianceAmendmentReasonChoicesView(views.APIView):
    permission_classes=[InternalCompliancePermission]

    def get(self,request, format=None):
        if is_internal(request):
            choices_list = []
            choices=ComplianceAmendmentReason.objects.all()
            if choices:
                for c in choices:
                    choices_list.append({'key': c.id,'value': c.reason})
            return Response(choices_list)
        return Response()


class GetComplianceStatusesDict(views.APIView):
    permission_classes=[IsAuthenticated]
    def get(self, request, format=None):
        data = {}
        if not cache.get('compliance_internal_statuses_dict') or not cache.get('compliance_external_statuses_dict'):
            cache.set('compliance_internal_statuses_dict',[{'code': i[0], 'description': i[1]} for i in Compliance.PROCESSING_STATUS_CHOICES], settings.LOV_CACHE_TIMEOUT)
            cache.set('compliance_external_statuses_dict',[{'code': i[0], 'description': i[1]} for i in Compliance.CUSTOMER_STATUS_CHOICES if i[0] != 'discarded'], settings.LOV_CACHE_TIMEOUT)
        data['external_statuses'] = cache.get('compliance_external_statuses_dict')
        if is_internal(request):
            data['internal_statuses'] = cache.get('compliance_internal_statuses_dict')
        return Response(data)


class ComplianceFilterBackend(DatatablesFilterBackend):
    def filter_queryset(self, request, queryset, view):

        filter_compliance_status = request.GET.get('filter_compliance_status')
        if filter_compliance_status and not filter_compliance_status.lower() == 'all':
            queryset = queryset.filter(processing_status=filter_compliance_status)
        
        try:
            super_queryset = super(ComplianceFilterBackend, self).filter_queryset(request, queryset, view)

            # Custom search 
            search_text = request.GET.get('search[value]')  # This has a search term.
            if search_text:
                system_user_ids = list(SystemUser.objects.annotate(full_name=Concat('legal_first_name',Value(" "),'legal_last_name',output_field=CharField()))
                .filter(
                    Q(legal_first_name__icontains=search_text) | Q(legal_last_name__icontains=search_text) | Q(email__icontains=search_text) | Q(full_name__icontains=search_text)
                ).values_list("ledger_id", flat=True))
                proposal_applicant_proposals = list(ProposalApplicant.objects.annotate(full_name=Concat('first_name',Value(" "),'last_name',output_field=CharField()))
                .filter(
                    Q(first_name__icontains=search_text) | Q(last_name__icontains=search_text) | Q(email__icontains=search_text) | Q(full_name__icontains=search_text)
                ).values_list("proposal_id", flat=True))
                q_set = queryset.filter(Q(approval__current_proposal__id__in=proposal_applicant_proposals)|Q(approval__current_proposal__submitter__in=system_user_ids))
                
                queryset = super_queryset.union(q_set)

            total_count = queryset.count()
            setattr(view, '_datatables_filtered_count', total_count)
        except Exception as e:
            logger.error(f'ComplianceFilterBackend raises an error: [{e}].  Query may not work correctly.')

        fields = self.get_fields(request)
        ordering = self.get_ordering(request, view, fields)

        #special handling for ordering by holder
        HOLDER = 'approval_holder'
        REVERSE_HOLDER = '-approval_holder'
        if HOLDER in ordering:
            ordering.remove(HOLDER)
            queryset = queryset.annotate(approval_holder=Concat('approval__current_proposal__proposal_applicant__first_name',Value(" "),'approval__current_proposal__proposal_applicant__last_name'))
            queryset = queryset.order_by(HOLDER)
        if REVERSE_HOLDER in ordering:
            ordering.remove(REVERSE_HOLDER)
            queryset = queryset.annotate(approval_holder=Concat('approval__current_proposal__proposal_applicant__first_name',Value(" "),'approval__current_proposal__proposal_applicant__last_name'))
            queryset = queryset.order_by(REVERSE_HOLDER)

        if len(ordering):
            queryset = queryset.order_by(*ordering)
        
        total_count = queryset.count()
        setattr(view, '_datatables_filtered_count', total_count)
        return queryset


class CompliancePaginatedViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (ComplianceFilterBackend,)
    pagination_class = DatatablesPageNumberPagination
    queryset = Compliance.objects.none()
    serializer_class = ListComplianceSerializer
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        request_user = self.request.user
        qs = Compliance.objects.none()

        target_email_user_id = int(self.request.GET.get('target_email_user_id', 0))

        if is_internal(self.request):
            if target_email_user_id:
                target_user = EmailUser.objects.get(id=target_email_user_id)
                qs = Compliance.objects.filter(Q(approval__proposal__proposal_applicant__email_user_id=target_user.id)).distinct()
            else:
                qs = Compliance.objects.all()
        elif is_customer(self.request):
            qs = Compliance.objects.filter(Q(approval__proposal__proposal_applicant__email_user_id=request_user.id)).exclude(processing_status="discarded").distinct()
        return qs
