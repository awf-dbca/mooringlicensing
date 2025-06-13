import Vue from 'vue'
import api from './api'
import {helpers} from '@/utils/hooks' 

export default {
    fetchProposal: function(id){
        return new Promise ((resolve,reject) => {
            Vue.http.get(helpers.add_endpoint_json(api.proposals,id)).then((response) => {
                resolve(response.body);
            },
            (error) => {
                reject(error);
            });
        });
    },
    fetchCountries: function (){
        return new Promise ((resolve,reject) => {
            Vue.http.get(api.countries).then((response) => {
                resolve(response.body);
            },
            (error) => {
                reject(error);
            });
        });

    },
    fetchUser: function(id){
        return new Promise ((resolve,reject) => {
            let request = utils.fetchUrl(helpers.add_endpoint_json(api.users,id))
            request.then((response) => {
                resolve(response.body);
            }).catch((error) => {
                console.log(error.message);
            });
        });
    },
    fetchProfile: function (){
        return new Promise ((resolve,reject) => {
            let request = utils.fetchUrl(api.profile)
            request.then((response) => {
                resolve(response.body);
            }).catch((error) => {
                console.log(error.message);
            });
        });

    },
}
