import React, {useState} from 'react';
// import {
//     Button,
//     Container,
//     ListGroup,
//     ListGroupItem,
//     InputGroup,
//     FormControl,
//     FormCheck,
//     FormLabel
// } from 'react-bootstrap';
import {
    Button,
    ListItem,
    ListItemText,
    TextField,
    FormControlLabel,
    List,
    Container,
    Switch,
    Divider,
    CssBaseline,
    MuiThemeProvider,
    createMuiTheme,
    Card, CardContent, Typography
} from '@material-ui/core'
import 'fontsource-roboto';
import './App.css';

// import 'bootstrap/dist/css/bootstrap.css';

function DishItem(props) {
    // const class_name = "list-group-item-action " + (props.dish.liked ? "list-group-item-success" : "list-group-item-danger");
    const color = props.dish.liked ? "success" : "error"
    const callback = () => {
        props.changeLiked(props.restaurant_id, props.dish_id, !props.dish.liked)
    };
    // const callback = ()=>{console.log('hi')};
    // return <ListGroupItem className={class_name} onClick={callback}>{props.dish.name}</ListGroupItem>;
    return <ListItem button color={color} onClick={callback}>
        <ListItemText color={color} primary={props.dish.name}></ListItemText>
        <Switch
            checked={props.dish.liked}
            color="primary"
        />
    </ListItem>
}

class NewDishLine extends React.Component {
    constructor(props) {
        super(props);
        this.state = {dish_name: ''}
        this.flexContainer = {display: 'flex', flexDirection: 'row'};


        this.handleChange = this.handleChange.bind(this);
        this.submit = this.submit.bind(this);
    }


    handleChange(event) {
        this.setState({dish_name: event.target.value})
    }

    submit() {
        const dish = {name: this.state.dish_name, liked: true};
        this.props.addDish(this.props.restaurant_id, dish);
        this.setState({dish_name: ''})
    }

    render() {
        return (
            // <InputGroup>
            //     <FormControl onChange={this.handleChange} placeholder="Add a dish..." value={this.state.dish_name}></FormControl>
            //     <Button onClick={this.submit}>Add</Button>
            // </InputGroup>
            <ListItem>
                <form style={this.flexContainer}>
                    <TextField placeholder={"Add a dish..."}
                               fullWidth={true}
                               value={this.state.dish_name}
                               onChange={this.handleChange}/>
                    <Button onClick={this.submit}>Add</Button>
                </form>
            </ListItem>
        );
    }
}

class RestaurantList extends React.Component {
    render() {
        return (
            <Card>
                <CardContent>
                                    <Typography gutterBottom variant="h4">
            {this.props.restaurant.name}
          </Typography>
                    <List component="nav">
                        {this.props.restaurant.dishes.map((d, i) => <DishItem dish={d}
                                                                              restaurant_id={this.props.restaurant_id}
                                                                              dish_id={i}
                                                                              changeLiked={this.props.changeLiked}/>)}
                        <Divider/>
                        <NewDishLine restaurant_id={this.props.restaurant_id} addDish={this.props.addDish}/>
                    </List>
                </CardContent>
            </Card>
        );
    }
}

class App extends React.Component {
    constructor(props) {
        super(props);
        this.state = {restaurants: this.loadData()}

        this.changeLiked = this.changeLiked.bind(this)
        this.addDish = this.addDish.bind(this)
    }

    loadData() {
        return [{name: 'Oishi', dishes: [{name: 'Tofu', liked: true}, {name: 'Curry', liked: false}]},
        {name: 'Oishi', dishes: [{name: 'Tofu', liked: true}, {name: 'Curry', liked: false}]},
        {name: 'Oishi', dishes: [{name: 'Tofu', liked: true}, {name: 'Curry', liked: false}]},
            {name: 'BioFrische', dishes: [{name: 'ChickenKorma', liked: true}]}];
    }

    changeLiked(r_id, d_id, new_liked) {
        let data = this.state.restaurants;
        data[r_id].dishes[d_id].liked = new_liked;
        this.setState({restaurants: data});
    }

    addDish(r_id, dish) {
        let data = this.state.restaurants;
        data[r_id].dishes.push(dish);
        this.setState({restaurants: data});
    }

    render() {
        return (
            <Container maxWidth="md" theme={this.default_theme}>
                <h1>Which dishes do you like?</h1>
                <div>
                    {this.state.restaurants.map((r, r_id) => <RestaurantList restaurant={r} restaurant_id={r_id}
                                                                             changeLiked={this.changeLiked}
                                                                             addDish={this.addDish}/>)}
                </div>
            </Container>
        );
    }
}

export default App;
