import Vue from 'vue'
import Router from 'vue-router'
import Profile from '@/components/user/profile.vue'
import external_routes from '@/components/external/routes'
import internal_routes from '@/components/internal/routes'
import MooringLicenceDocumentsUpload from '@/components/external/mooring_licence_documents_upload'
import DcvAdmissionForm from '@/components/external/dcv/dcv_admission'
import * as VueRouter from 'vue-router';

const router = VueRouter.createRouter({
    history: VueRouter.createWebHistory(),
    routes: [
        {
          path: '/firsttime',
          name: 'first-time',
          component: Profile
        },
        {
          path: '/account',
          name: 'account',
          component: Profile
        },
        external_routes,
        internal_routes,
        {
            path: '/mla_documents_upload/:uuid',
            name: 'mla-documents-upload',
            component: MooringLicenceDocumentsUpload
        },
        {
            path: '/dcv_admission_form',
            name: 'dcv-admission-form',
            component: DcvAdmissionForm
        }
    ]
})

export default router;