module.exports = {
    fetchUrl: async function (url, options) {
        return new Promise((resolve, reject) => {
            let f = options === undefined ? fetch(url) : fetch(url, options);
            f.then(
                async (response) => {
                    const data = await response.json();
                    if (!response.ok) {
                        let error =
                            (data.constructor.name === 'Array' && data) ||
                            (data && data.message) ||
                            response.statusText;
                        console.error(error);
                        reject(error);
                    }
                    resolve(data);
                },
                (error) => {
                    console.error(
                        `There was an error fetching from ${url}`,
                        error
                    );
                    error = new Error(ERRORS.NETWORK_ERROR);
                    reject(error);
                }
            );
        });
    },
}