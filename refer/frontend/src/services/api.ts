import axios from 'axios';

export interface Comment {
  text: string;
  sentiment: string;
}
  
export interface Keyword {
  text: string;
  count: number;
}

export interface QueryResponse {
  sentiment: 'positive' | 'negative';
  comments: Comment[];
  keywords: Keyword[];
  subreddits: string[];
  recordCount: number;
}

export interface QueryPayload{
  query: string;
  subreddit?: string[];
  date?: string;
}



  export const ApiClient = {

    getQueryResponse: async(payload: QueryPayload): Promise<QueryResponse> => {

      try{

        
        // Placeholder till the backend is finished
        // const response = await axios.post('http://localhost:8000/api/query', {payload})
        const response = await axios.post('http://backend:8000/api/query', {payload})
        console.log('Response from backend:', response.data);
        return response.data;


        // DUMMY DATA
        // return new Promise((resolve) => {
        //   setTimeout( () => {
        //     resolve({
        //       sentiment: 'positive',
        //       comments: [
        //         { text: "IBKR's interface is much better for trading options", sentiment: "Positive" },
        //         { text: "Tiger's mobile app has improved significantly", sentiment: "Positive" },
        //         { text: "The execution speed on IBKR is unmatched", sentiment: "Positive" },
        //       ],
        //       keywords: [
        //         { keyword: "interface", count: 45 },
        //         { keyword: "trading", count: 38 },
        //         { keyword: "this", count: 32 },
        //         { keyword: "is", count: 28 },
        //         { keyword: "dummy", count: 25 },
        //         { keyword: "data", count: 2 },
        //       ],
        //       subreddits: ['r/investing', 'r/stocks', 'r/options'],
        //       recordCount: 100
        //     });
        //   }, 1500);
        //   });



      }catch (error) {
        console.error('Error fetching query response:', error);
        throw error;
      }

    }
  }

  