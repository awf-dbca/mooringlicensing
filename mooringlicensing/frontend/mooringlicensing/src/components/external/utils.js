import Vue from 'vue'
import api from './api'
import {helpers,utils} from '@/utils/hooks' 

export default {
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
    fetchProposal: function(id){
        return new Promise ((resolve,reject) => {
            let request = utils.fetchUrl(helpers.add_endpoint_json(api.proposals,id))
            request.then((response) => {
                resolve(response.body);
            }).catch((error) => {
                console.log(error.message);
            });
        });
    },
    fetchCountries: function (){
        return new Promise ((resolve,reject) => {
            let request = utils.fetchUrl(api.countries).then((response) => {
                resolve(response.body);
            }).catch((error) => {
                console.log(error.message);
            });
        });

    },
}
