using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;


public class Bibity : MonoBehaviour {

 	public float speed;//setting the speed the character will rotate
	private Rigidbody2D rb;
	void Start () {
		rb = GetComponent<Rigidbody2D> ();
	}
	
	// Update is called once per frame
void FixedUpdate(){
	float moveHorizontal = Input.GetAxis("Horizontal");
	float moveVertical = Input.GetAxis("Vertical");
	Vector2 movement = new Vector2(moveHorizontal, moveVertical);
	rb.AddForce(movement*speed);
	}
}