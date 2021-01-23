import React, {useState} from 'react';
import {Button, Container, ListGroup, ListGroupItem} from 'react-bootstrap';
import './App.css';
import 'bootstrap/dist/css/bootstrap.css';

function DishItem(props){
    const class_name = "list-group-item-action "+ (props.dish.liked ? "list-group-item-success" : "list-group-item-danger");
    const callback = ()=>{props.changeLiked(props.restaurant_id, props.dish_id, !props.dish.liked)};
    // const callback = ()=>{console.log('hi')};
    return <ListGroupItem className={class_name} onClick={callback}>{props.dish.name}</ListGroupItem>;
}

function RestaurantList(props) {
    return (
        <div>
        <h3>{props.restaurant_name}</h3>
        <ListGroup>
            {props.dishes.map((d,i)=><DishItem dish={d} restaurant_id={props.restaurant_id} dish_id={i} changeLiked={props.changeLiked}/>)}
        </ListGroup>
        </div>
    );
}

function App() {
    const [restaurants, setRestaurants] = useState([{name:'Oishi', dishes:[{name:'Tofu', liked:true}, {name:'Curry', liked:false}]}, {name:'BioFrische', dishes:[{name:'ChickenKorma', liked: true}]}]);
    const updateDishes = (dishes, d_id, new_liked) => dishes.map((d,i)=> i==d_id ? {...d, liked:new_liked} : d);
    const changeLiked = (r_id, d_id, new_liked) => setRestaurants(prevState=>prevState.map((r,i)=>i==r_id ? {...r, dishes: updateDishes(r.dishes, d_id, new_liked)} : r));
    return (
        <Container>
            <h1>Title</h1>
            <div className="App">
                <Button>Hello World</Button>
            </div>
            <div>
            {restaurants.map((r,r_id)=><RestaurantList restaurant_name={r.name} dishes={r.dishes} restaurant_id={r_id} changeLiked={changeLiked}/>)}
            </div>
        </Container>
    );
}

export default App;
